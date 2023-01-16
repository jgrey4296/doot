#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import shutil
import abc
import logging as logmod
import sys
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

from doit.action import CmdAction

import doot
from doot.tasker import DootTasker
from doot import globber

adb_path = shutil.which("adb")

android_base = pl.Path(doot.config.or_get("/storage/6331-3162").tools.doot.android.base())
adb_key      = doot.config.or_get("/Users/johngrey/.android/adbkey").tools.doot.android.key()
timeout      = doot.config.or_get(5).tools.doot.android.timeout()
port         = doot.config.or_get(37769).tools.doot.android.port()
wait_time    = doot.config.or_get(10).tools.doot.android.wait()

NICE = ["nice", "-n", "10"]

class ADBUpload(globber.DirGlobber):
    """
    Push files from local to device
    """

    def __init__(self, name="android::upload", dirs=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], rec=rec)
        self.device_root = None
        self.report      = {}

    def filter(self, fpath):
        if fpath in self.roots:
            return self.control.discard
        return self.control.keep

    def set_params(self):
        return [
            {"name": "id", "long": "id", "type": str, "default": None},
            {"name": "remote", "long": "remote", "type": str, "default": None},
        ]

    def task_detail(self, task):
        self.device_root = android_base / self.params['remote']
        task.update({
            "actions" : [ self.write_report ],
        })
        return task

    def subtask_detail(self, task, fpath):
        # relative fpath from root
        rel = self.rel_path(fpath)

        task.update({
            "actions" : [ CmdAction((self.push_dir, [rel], {}), shell=False) ],
        })
        return task

    def push_dir(self, relpath):
        cmd = [ adb_path, "-t", self.params['id'],
                "push", "--sync",
                pl.Path(self.params['local']) / relpath,
                (device_root / relpath).parent ]
        print(f"Push Cmd: {cmd}")
        return cmd

    def write_report(self):
        return

class ADBDownload(DootTasker):
    """
    pull files from device to local
    """

    def __init__(self, name="android::download", dirs=None):
        super().__init__(name, dirs)
        self.report      = {}
        self.device_root = None
        self.local_root  = None

    def set_params(self):
        return [
            # {"name": "ipaddr", "long": "ip", "type": str, "default":  "192.168.1.22"},
            {"name": "id", "long": "id", "type": str, "default": None},
            {"name": "remote", "long": "remote", "type": str, "default": "__na"},
            {"name" : "local", "long": "local", "type": str, "default": "__na"},
        ]

    def task_detail(self, task):
        self.device_root = android_base / self.params['remote']
        self.local_root  = pl.Path(self.params['local'])
        task.update({
            "actions" : [ CmdAction(self.query_files, shell=False, save_out="immediate_files"),
                          CmdAction(self.query_sub_dirs, shell=False, save_out="remote_subdirs"),
                          self.batch_query_subdirs, # -> remote_files
                          self.calc_missing, # -> missing
                          self.pull_missing,
                          self.write_report,
                         ],
            "verbosity" : 2,
        })
        return task

    def query_sub_dirs(self):
        cmd = [adb_path, "-t", self.params['id'],
               "shell", "find",
                self.device_root,
               "-maxdepth", "1",
               "-type", "d"
               ]

        return cmd

    def query_files(self):
        cmd = [adb_path, "-t", self.params['id'],
               "shell", "find",
                self.device_root,
               "-maxdepth", "1",
               "-type", "f"
               ]

        return cmd

    def batch_query_subdirs(self, task):
        immediate_files = task.values['immediate_files']
        subdirs         = {pl.Path(x.strip()) for x in task.values['remote_subdirs'].split("\n") if bool(x.strip())}
        subdirs.remove(self.device_root)

        remote_files = [immediate_files]
        if bool(subdirs):
            print(f"Subdirs to Batch: {subdirs}", file=sys.stderr)
            remote_files += self.run_batch(*[[x] for x in subdirs], fn=self.subdir_batch)

        return { "remote_files" : "\n".join(remote_files) }

    def subdir_batch(self, data):
        print(f"Subdir Batch: {data}", file=sys.stderr)
        query = CmdAction([adb_path, "-t", self.params['id'],
                           "shell", "find", data[0],
                           "-type", "d"
                          ], shell=False)

        query.execute()
        return query.out

    def calc_missing(self, task):
        device_set = { pl.Path(x.strip()).relative_to(self.device_root) for x in task.values['remote_files'].split("\n") if bool(x.strip()) }
        local_set  = { x.relative_to(self.local_root) for x in self.local_root.rglob("*") }

        missing = device_set - local_set
        print(f"Missing: {missing}")
        return { "missing" : [str(x) for x in missing] }

    def pull_missing(self, task):
        missing = task.values['missing']

        for mpath in missing:
            src  = self.device_root / mpath
            dest = self.local_root / mpath
            if not dest.parent.exists():
                dest.parent.mkdir(parents=True)

            cmd_args = [adb_path, "-t", self.params['id'],
                        "pull",
                        src,
                        dest,
                        ]

            cmd = CmdAction(cmd_args, shell=False)
            cmd.execute()

    def write_report(self, task):
        pass
