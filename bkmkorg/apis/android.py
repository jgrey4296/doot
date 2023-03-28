#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import shutil
import time
import types
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import sys
import time
from collections import defaultdict

import doot
from doot.mixins.commander import CommanderMixin
from doot.mixins.batch import BatchMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.targeted import TargetedMixin

android_base   : Final = doot.config.on_fail("/storage/6331-3162", str).tools.doot.android.base(wrapper=pl.Path)
batch_sleep    : Final = doot.config.on_fail(2, int|float).subtask.sleep()
pull_group_max : Final = doot.config.on_fail(100, int).android.pull.max_group()
adb_path       : Final = shutil.which("adb")

class ADBMixin:
    """
    Mixin for tasks using ADB to push/pull to android
    """

    device_root = None
    local_root  = None

    def adb_params(self) -> list:
        return [
            {"name": "id", "long": "id", "type": str, "default": None},
        ]

    def args_adb_query(self, target:str|pl.Path=".", depth=1, ftype="d") -> list:
        """
        return cmd arg list to find all {depth} {ftype} of android_root / {target}
        """
        cmd = [adb_path, "-t", self.args['id'], "shell", "find"]
        match str(target)[0]:
            case "/":
                cmd.append(target)
            case _:
                cmd.append(str(self.device_root / target))

        if depth >= 0:
            cmd += ["-maxdepth", str(depth)]
        if bool(ftype):
            cmd += ["-type", ftype]

        print(f"ADB Query: {cmd}")
        return cmd

    def args_adb_push_dir(self, fpath:str|pl.Path="."):
        """
        Build adb cmd to push {local}/{relpath} to {device}/{relpath}
        strictly speaking {device}/{relpath.parent}, creating {relpath}
        """
        self.count += 1
        print(f"building push for: {fpath}")
        cmd = [ adb_path, "-t", self.args['id'], "push", "--sync"]
        match str(fpath)[0]:
            case "/":
                relpath = self.rel_path(fpath)
                cmd.append(fpath)
                cmd.append((self.device_root / relpath).parent)
            case _:
                cmd.append(self.local_root / fpath)
                cmd.append((self.device_root / fpath).parent)

        print(f"ADB Push: {cmd}")
        return cmd

    def args_adb_pull(self, fpath:str|pl.Path="."):
        """
        build a cmd list to pull a file or directory from the device to local
        """
        match str(fpath)[0]:
            case "/":
                rel_path = pl.Path(fpath).relative_to(self.device_root)
                src  = fpath
                dest = self.local_root / rel_path
            case _:
                src  = self.device_root / fpath
                dest = self.local_root / fpath

        if not dest.parent.exists():
            dest.parent.mkdir(parents=True)

        cmd = [adb_path, "-t", self.args['id'], "pull"]
        cmd.append(src)
        cmd.append(dest)
        print(f"ADB Pull: {cmd}")
        return cmd

    def args_adb_pull_group(self, dest:pl.Path, group:list[pl.Path]):
        """
        build a cmd list to pull a file or directory from the device to local
        """
        if not dest.exists():
            dest.mkdir(parents=True)
        cmd = [adb_path, "-t", self.args['id'], "pull"]
        cmd += list(group)
        cmd.append(dest)
        print(f"Group Pull: {cmd[:20]} {cmd[-1]}")
        return cmd

    def args_adb_mv(self, dest:pl.Path, paths:list[pl.Path]):
        cmd = [adb_path, "-t", self.args['id'], "shell", "mv"]
        cmd += ["-t", dest, "-n"]
        cmd += paths
        return cmd


    def batch_query_subdirs(self, fn, task) -> dict:
        """"
        Batch query all found directories that aren't the device root
        adds task.values['remote_files']
        """
        immediate_files = {x.strip() for x in task.values['immediate_files'].split("\n")}
        subdirs         = {x.strip() for x in task.values['remote_subdirs'].split("\n") if bool(x.strip())}
        subdirs.remove(str(self.device_root))

        remote_files = set()
        remote_files.update(immediate_files)
        if bool(subdirs):
            print(f"Subdirs to Batch: {subdirs}", file=sys.stderr)
            remote_files.update(self.run_batches(*[[x] for x in subdirs], fn=fn))

        return { "remote_files" : [x for x in remote_files if bool(x)] }

    def pull_files(self, task):
        """
        pull paths in task.values['pull_targets'] to equivalent
        adds task.values['downloaded', 'failed']
        """
        grouped = defaultdict(lambda: set())
        for value in task.values['pull_targets']:
            as_path = pl.Path(value)
            grouped[as_path.parent].add(self.device_root / as_path)

        downloaded = []
        failures   = []

        self.say("Ready to Inspect").execute()
        breakpoint()
        pass
        for parent, vals in grouped.items():
            try:
                dest     = self.local_root / parent
                if len(vals) < pull_group_max:
                    core_cmd = self.args_adb_pull_group(dest, vals)
                    cmd      = self.cmd(core_cmd)
                    cmd.execute()
                else:
                    logging.info("Pulling in chunks of %s", pull_group_max)
                    self._pull_files_chunked(dest, vals)

                downloaded.append(f"{vals}")
                time.sleep(batch_sleep)
            except Exception as err:
                logging.warning("Failed Pull Due to: %s", err)
                failures.append(f"{parent} : {vals}")

        return { "downloaded" : downloaded, "failed": failures }

    def _pull_files_chunked(self, dest, vals):
        for chunk in self.chunk(vals, pull_group_max):
            logging.info("Chunk...")
            guard = [x for x in chunk if x is not None]
            core_cmd = self.args_adb_pull_group(dest, guard)
            cmd      = self.cmd(core_cmd)
            cmd.execute()
    
    def adb_delete_files(self):
        """
        delete files specified in task.values['delete_targets']
        """
        logging.info("Moving %s Files to directory to delete", len(self.targets))
        mv_to       = android_base / "to_delete"
        mk_dest_cmd = [adb_path, "-t", self.args['id'], "shell", "mkdir", mv_to]
        self.cmd(mk_dest_cmd).execute()

        deleted = []
        try:
            for chunk in self.chunk(self.targets):
                logging.info("Chunk...")
                deleted += chunk
                mv_cmd      = self.args_adb_mv(mv_to, [x for x in chunk if x is not None])
                self.cmd(mv_cmd).execute()

        finally:
            (self.locs.temp / "deletions.log").write_text("\n".join(str(x) for x in deleted))
