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

import doot
from doot.tasker import DootTasker
from doot import globber
from doot.mixins.apis import android
from doot.mixins.batch import  BatchMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin


android_base : Final = doot.config.on_fail("/storage/6331-3162", str).tools.doot.android.base(wrapper=pl.Path)
timeout      : Final = doot.config.on_fail(5, int).tools.doot.android.timeout()
port         : Final = doot.config.on_fail(37769, int).tools.doot.android.port()
wait_time    : Final = doot.config.on_fail(10, int).tools.doot.android.wait()

NICE         : Final = ["nice", "-n", "10"]

class ADBUpload(android.ADBMixin, BatchMixin, DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin):
    """
    Push files from local to device
    """

    def __init__(self, name="android::upload", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.local_push], rec=rec)
        self.device_root = None
        self.local_root  = None
        self.report      = list()
        self.count       = 0

    def filter(self, fpath):
        is_build = fpath.name == self.locs.build.name
        is_temp  = fpath.name == self.locs.temp.name
        if not (is_build or is_temp) and fpath.is_dir() and fpath.parent in self.roots:
            return self.control.keep
        return self.control.discard

    def set_params(self):
        return [
            {"name": "id", "long": "id", "type": str, "default": None},
            {"name": "remote", "long": "remote", "type": str, "default": "."},
        ] + self.target_params()


    def setup_detail(self, task):
        self.device_root = android_base / self.args['remote']
        self.local_root  = self.locs.local_push
        task.update({
            "actions" : [
                (self.log, [f"Set Device Root to: {self.device_root}", logmod.INFO]),
            ],
            "teardown" : [ self.write_report ],
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [
                (self.upload_target, [fpath]),
            ],
        })
        return task

    def sub_filter(self, fpath):
        if fpath.is_dir():
            return self.globc.accept
        return self.globc.discard

    def upload_target(self, fpath):
        logging.info("Uploading Chunks of %s", fpath)
        chunks = self.chunk(self.glob_target(fpath, fn=self.sub_filter, rec=False))
        self.run_batches(*chunks)

    def batch(self, data):
        for fpath in data:
            cmd = self.cmd(self.args_adb_push_dir, fpath, save="result")
            cmd.execute()
            entry = f"{fpath}: {cmd.out}"
            self.report.append(entry)

    def write_report(self):
        logging.info("Completed")
        report = []
        report.append("--------------------")
        report.append("Pushed: ")
        report += [str(x) for x in self.report]

        (self.locs.build / "adb_push.report").write_text("\n".join(report))

class ADBDownload(android.ADBMixin, DootTasker, CommanderMixin, FilerMixin, BatchMixin):
    """
    pull files from device to local
    """

    def __init__(self, name="android::download", locs=None):
        super().__init__(name, locs)
        self.report      = {}
        self.device_root = None
        self.local_root  = None
        self.locs.ensure("local_pull")

    def set_params(self):
        return [
            {"name": "id", "long": "id", "type": str, "default": None},
            {"name": "remote", "long": "remote", "type": str, "default": "."},
            {"name" : "local", "long": "local", "type": str, "default": str(self.locs.local_pull)},
        ]

    def task_detail(self, task):
        self.device_root = android_base / self.args['remote']
        self.local_root  = pl.Path(self.args['local'])

        if (self.locs.build / "pull_cache.adb").exists():
            # Cached query results
            query_cmds = [
                self.say("Using Pull Cache"),
                self.read_cache, # -> remote_files
            ]
        else:
            query_cmds = [self.cmd(self.args_adb_query, ftype="f", save="immediate_files"),
                          self.cmd(self.args_adb_query,            save="remote_subdirs"),
                          (self.batch_query_subdirs, [self._subbatch_query] ), # -> remote_files
                          self.write_query_cache,
                          self.say("Finished Queries"),
                          ]

        task.update({
            "actions" : [
                *query_cmds,
                self.calc_pull_targets, # -> pull_targets
                self.say("Starting Pull"),
                self.pull_files, # -> downloaded, failed
                self.write_report,
            ],
            "verbosity" : 2,
        })
        return task

    def _subbatch_query(self, data):
        """
        Run a single query directory query
        """
        logging.info(f"Subdir Batch: {data}")
        query = self.cmd(self.args_adb_query(data[0], depth=-1, ftype="f"))
        query.execute()
        query_result = {x.strip() for x in query.out.split("\n")}
        return query_result

    def calc_pull_targets(self, task):
        device_set = { pl.Path(x.strip()).relative_to(self.device_root) for x in task.values['remote_files']}
        local_set  = { x.relative_to(self.local_root) for x in self.local_root.rglob("*") }

        pull_set = device_set - local_set
        logging.info(f"Pull Set: {len(pull_set)}")
        if not bool(pull_set):
            return False

        return { "pull_targets" : [str(x) for x in pull_set] }

    def write_report(self, task):
        report = []
        report.append("--------------------")
        report.append("Pull Targets From Device: ")
        report += task.values['pull_targets']

        report.append("--------------------")
        report.append("Downloaded: ")
        report += task.values['downloaded']

        report.append("--------------------")
        report.append("Failed: ")
        report += task.values['failed']

        (self.locs.build / "adb_pull.report").write_text("\n".join(report))

    def write_query_cache(self, task):
        cache_str = "\n".join(x for x in task.values['remote_files'])
        (self.locs.build / "pull_cache.adb").write_text(cache_str)

    def read_cache(self):
        cache   = self.locs.build / "pull_cache.adb"
        targets = [x.strip() for x in cache.read_text().split("\n")]
        return { 'remote_files': [x for x in targets if bool(x) ]}

class ADBDelete(android.ADBMixin, DootTasker, CommanderMixin, FilerMixin, BatchMixin):
    """
    delete all files specified in the provided list
    """

    def __init__(self, name="android::delete", locs=None):
        super().__init__(name, locs)
        self.report      = {}
        self.device_root = None
        self.targets     = []

    def set_params(self):
        return [
            {"name": "id", "long": "id", "type": str, "default": None},
            {"name": "remote", "long": "remote", "type": str, "default": "."},
            {"name": "targetList", "long": "list", "type": pl.Path, "default": None},
        ]

    def task_detail(self, task):
        self.device_root = android_base / self.args['remote']
        task.update({
            "actions": [
                self.read_target,
                self.adb_delete_files,
            ],
        })
        return task

    def read_target(self):
        lines        = self.args['targetList'].read_text().split("\n")
        self.targets = [self.device_root / fname.strip() for fname in lines]
