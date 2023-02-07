# -*- mode:doot; -*-
#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
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

import time

import sys
import shutil
import doot
from doot import tasker, globber, task_mixins


class BackupTask(task_mixins.BatchMixin, globber.LazyGlobMixin, globber.DootEagerGlobber):
    """
    copy all files to the target if they are newer or don't exist
    """
    def __init__(self, name="backup::default", locs=None, roots=None, output=None):
        super().__init__(name, locs, roots, rec=True, output=output)

    def task_detail(self, task):
        task.update({
            "actions" : [ self.backup_files ],
            "verbosity" : 1,
        })
        return task

    def filter(self, fpath):
        rel_path      = self.rel_path(fpath)
        target        = self.output / rel_path

        if not target.exists():
            return self.control.keep

        if fpath.is_dir():
            return self.control.discard

        # Compare mod times
        base   = fpath.stat().st_mtime
        backup = target.stat().st_mtime

        if backup < base:
            return self.control.keep

        return self.control.reject

    def backup_files(self):
        globbed = super(globber.LazyGlobMixin, self).glob_all()
        if not bool(globbed):
            print("No Changes", file=sys.stderr)

        chunked = self.chunk(globbed, 100)
        self.run_batches(*chunked)

    def batch(self, data):
        for name, fpath in data:
            rel_path      = self.rel_path(fpath)
            target        = self.output / rel_path
            target_parent = target.parent
            if not target_parent.exists():
                print(f"Making Directory: {target_parent}")
                target_parent.mkdir(parents=True)

            if fpath.is_dir():
                print(f"Copying Tree: {fpath} -> {target}")
                shutil.copytree(fpath, target)
                continue

            print(f"Copying File: {fpath}")
            shutil.copy(fpath, target)
