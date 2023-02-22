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
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin

batch_size       = doot.config.on_fail(10, int).tool.doot.batch.size()
sleep_batch      = doot.config.on_fail(2.0,   int|float).tool.doot.batch.sleep()

class BackupTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber):
    """
    copy all files to the target if they are newer or don't exist
    """

    def __init__(self, name="backup::default", locs=None, roots=None, output=None):
        super().__init__(name, locs, roots, rec=True, output=output)

    def set_params(self):
        return self.target_params()

    def task_detail(self, task):
        task.update({})
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


    def subtask_detail(self, task, fpath):
        actions = []
        if fpath.is_dir():
            actions.append( (self.backup_dir, [fpath]) )
        else:
            actions.append( (self.backup_file, [fpath]) )

        if task.get('meta', {}).get('n', 1) % batch_size == 0;
            actions.append(lambda: sleep(sleep_batch))

        task.update({
            "actions" : actions,
        })
        return fpath

    def backup_file(self, fpath):
        rel_path      = self.rel_path(fpath)
        target        = self.output / rel_path
        target_parent = target.parent
        if not target_parent.exists():
            logging.debug(f"Making Directory: {target_parent}")
            target_parent.mkdir(parents=True)

        logging.debug(f"Copying File: {fpath}")
        shutil.copy(fpath, target)

    def backup_dir(self, fpath):
        rel_path      = self.rel_path(fpath)
        target        = self.output / rel_path
        target_parent = target.parent
        if not target_parent.exists():
            logging.debug(f"Making Directory: {target_parent}")
            target_parent.mkdir(parents=True)

        logging.debug(f"Copying Tree: {fpath} -> {target}")
        shutil.copytree(fpath, target)
