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

from doot import tasker
from doot.mixins.filer import FilerMixin

class DeleterTask(tasker.DootTasker, FilerMixin):
    """
    Delete files listed in the target
    """

    def __init__(self, name="file::deleter", locs=None, target=None):
        super().__init__(name, locs)
        self.deletion_list = []
        self._target       = target
        self.locs.ensure("temp", "build", task=name)

    def set_params(self):
        return [
            {"name": "target", "short": "t",      "type": pl.Path, "default": self._target},
            {"name": "backup", "long" : "backup", "type": bool, "default": True, "inverse": "no-backup"},
        ]

    def task_detail(self, task):
        if self.args['target'] is None:
            return None

        task.update({
            "actions" : [
                self.load_deletions,
                self.delete_files,
                (self.write_to, [self.locs.build / "deletion.log", "deletions"])
            ],
        })
        return task

    def load_deletions(self):
        if not self.args['target'].exists():
            return False

        lines              = self.args['target'].read_text().split("\n")
        self.deletion_list = [pl.Path(fname.strip()).expanduser().resolve() for fname in lines if bool(fname.strip())]

    def delete_files(self):
        logging.info("Got %s files to delete", len(self.deletion_list))
        log = []
        move_target : pl.Path = self.locs.build / "to_delete"
        move_target.mkdir(exist_ok=True)

        for path in self.deletion_list:
            assert(path.exists())
            if path.is_dir():
                raise TypeError(f"Path is a directory: {path}")
            if self.args['backup']:
                fpath.rename(move_target / fpath.name)
            else:
                path.unlink()
            log.append(str(path))

        return { "deletions" : "\n".join(log) }
