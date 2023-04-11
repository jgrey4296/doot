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

    def __init__(self, name="file::deleter", locs=None):
        super().__init__(name, locs)

    def set_params(self):
        return [
            {"name": "target", "short": "t", "type": pl.Path, "default": None},
        ]

    def task_detail(self, task):
        task.update({
            "actions" : [ self.delete_files,],
        })
        return task

    def delete_files(self):
        target = self.args['target']
        if target is None or not target.exists():
            return False
        text   = target.read_text()
        paths  = [pl.Path(x.strip()) for x in text.split("\n") if bool(x.strip())]

        logging.info("Got %s files to delete", len(paths))
        for path in paths:
            assert(path.exists())
            if path.is_dir():
                raise TypeError(f"Path is a directory: {path}")
            path.unlink()
