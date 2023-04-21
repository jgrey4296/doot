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
from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin

batch_size       = doot.config.on_fail(10, int).batch.size()
sleep_batch      = doot.config.on_fail(2.0,   int|float).batch.sleep()

class BackupCollectorTask(tasker.DootTasker, CommanderMixin, FilerMixin):
    """
    alternate backup task, using a calls to `find`
    # TODO option for backup as zip
    """

    def __init__(self, name="backup::collect.default", locs=None, source=None, backup=None):
        super().__init__(name, locs)
        self.source       = source
        self.backup       = backup
        self.source_cache = self.locs.temp / f"{name}_source.cache"
        self.backup_cache = self.locs.temp / f"{name}_backup.cache"
        self.calc_cache   = self.locs.temp / f"{name}_calc.cache"
        self.sep = "|:|"
        self.find_args    = [ "-path", "*__pycache__", "-prune", "-o", "-not", "-name", ".DS_Store", "-a", "-type", "f", "-printf", f"%P {self.sep} %T@\n" ]

    def set_params(self):
        return [
            {"name": "fresh",     "long": "fresh",     "type": bool, "default": True, 'inverse': "stale"},
            {"name": "re-source", "long": "re-source", "type": bool, "default": False},
            {"name": "re-backup", "long": "re-backup", "type": bool, "default": False},
            {"name": "calc-only", "long": "calc-only", "type": bool, "default": False},
            {"name": "reverse",   "long": "reverse",   "type": bool, "default": False, "help": "only calc"},
        ]

    def task_detail(self, task):
        self.args['re-source'] = self.args['fresh'] or self.args['re-source'] or not self.source_cache.exists()
        self.args['re-backup'] = self.args['fresh'] or self.args['re-backup'] or not self.backup_cache.exists()
        if self.args['reverse']:
            logging.info("Reversing")
            self.args['calc-only'] = True
            source = self.source
            self.source = self.backup
            self.backup = source

        skip_calc = self.calc_cache.exists() and not (self.args['re-source'] or self.args['re-backup'])

        actions = [(self.log, [f"Processing: {self.source} : {self.backup}", logmod.INFO])]

        if self.args['re-source']: # -> source.find
            actions += [ (self.log, ["Generating Source Cache", logmod.INFO]), self.make_cmd("find", self.source, *self.find_args, save="source.find"), (self.write_to, [self.source_cache, "source.find"])]
        elif not skip_calc:
            actions += [ (self.log, ["Reading Source Cache", logmod.INFO]), (self.read_from, [self.source_cache, "source.find"]) ]

        if self.args['re-backup']: # -> backup.find
            actions += [ (self.log, ["Generating Backup Cache", logmod.INFO]), self.make_cmd("find", self.backup, *self.find_args, save="backup.find"), (self.write_to, [self.backup_cache, "backup.find"])]
        elif not skip_calc:
            actions += [ (self.log, ["Reading Backup Cache", logmod.INFO]), (self.read_from, [self.backup_cache, "backup.find"]) ]

        if skip_calc: # -> to_backup
            actions  = [ (self.log, ["Reading Calculated Cache", logmod.INFO]), (self.read_from, [self.calc_cache, "to_backup"], {"fn":lambda x: x.split("\n")}) ]
        else:
            actions += [self.calculate_updates, (self.write_to, [self.calc_cache, "to_backup"], {"sub_sep":"\n"})]

        if not self.args['calc-only']:
            actions += [ self.backup_files ]

        task.update({
            "actions"   : actions,
            "targets"   : [ self.source_cache, self.backup_cache, self.calc_cache ],
            "verbosity" : 1,
        })
        return task

    def calculate_updates(self, task):
        source_list = dict((x,float(y)) for line in task.values['source.find'].split("\n") if bool(line) for (x,y) in [line.split(self.sep)])
        backup_list = dict((x,float(y)) for line in task.values['backup.find'].split("\n") if bool(line) for (x,y) in [line.split(self.sep)])
        logging.info("Calculating Updates: %s // %s", len(source_list), len(backup_list))

        source_keys      = list(source_list.keys())
        backup_keys      = list(backup_list.keys())
        newer_or_missing = set(x for x in source_keys if x not in backup_keys or source_list[x] > backup_list[x])
        logging.info("Files to Update: %s", len(newer_or_missing))

        del task.values['source.find']
        del task.values['backup.find']

        return { "to_backup": list(newer_or_missing) }


    def backup_files(self, task):
        src_abs         = self.source.resolve()
        backup_abs      = self.backup.resolve()
        whitelist_files = [src_abs / x.strip() for x in task.values['to_backup']]
        whitelist_dirs  = [x for f in whitelist_files for x in f.parents if x.is_relative_to(src_abs)]
        whitelist       = set(map(str, whitelist_files + whitelist_dirs))
        logging.debug("Whitelist: %s", whitelist)

        def ignore_fun(folder, files):
            fpath = pl.Path(folder)
            logging.info("Backing Up: %s", fpath.relative_to(src_abs))
            result = [x for x in files if str(fpath / x) not in whitelist]
            logging.debug("Ignoring: %s : %s : %s", result, folder, files)
            return result

        logging.info("Starting Backup: %s -> %s", self.source, self.backup)
        shutil.copytree(src_abs, backup_abs, ignore=ignore_fun, dirs_exist_ok=True)
