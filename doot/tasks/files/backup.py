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
from doot import tasker, globber
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin

batch_size       = doot.config.on_fail(10, int).batch.size()
sleep_batch      = doot.config.on_fail(2.0,   int|float).batch.sleep()

class BackupTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber):
    """
    copy all files to the target if they are newer or don't exist
    # TODO option for backup as zip
    """

    def __init__(self, name="backup::default", locs=None, roots=None, output=None):
        super().__init__(name, locs, roots, rec=True, output=output)
        self._backup_log = []

    def set_params(self):
        return self.target_params()

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


    def task_detail(self, task):
        task.update({
            "actions" : [ (self.log, [[lambda: self._backup_log], logmod.INFO, "Backed Up: " ]) ],
        })
        return task

    def subtask_detail(self, task, fpath):
        """
        Build the backup instruction.
        Either backup the entire directory, or a single file
        if you hit modulo of batch size, sleep
        """
        actions = [ lambda: self._backup_log.append(fpath) ]
        if fpath.is_dir():
            actions.append( (self.log, [f"Backup Up Directory: {fpath}"]) )
            actions.append( (self.backup_dir, [fpath]) )
        else:
            actions.append( (self.backup_file, [fpath]) )

        if task.get('meta', {}).get('n', 1) % batch_size == 0:
            actions.append( (self.log, ["...", logmod.INFO]) )
            actions.append( lambda: time.sleep(sleep_batch) )

        task.update({
            "actions" : actions,
        })
        return task

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
        try:
            shutil.copytree(fpath, target)
        except shutil.Error as err:
            logging.warning("Directory Backup Issue: %s", err)
