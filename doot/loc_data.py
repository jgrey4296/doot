#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field, replace
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

from doit.task import Task as DoitTask
from doit.task import dict_to_task

from doot.task_group import TaskGroup
from doot.utils.dir_tasks import CheckDir
from doot.tasker import DootTasker
from doot.errors import DootDirAbsent

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

class DootLocData:
    """
    Manage locations in a dict-like class, with attribute access,
    that can build tasks for location checks
    """

    _all_registered : ClassVar[dict[str, DootLocData]] = {}
    _default_locs   : ClassVar[list[str]]
    _locs_name  = "_locs::report"

    @staticmethod
    def set_defaults(config:TomlAccess):
        DootLocData._default_locs = config.or_get([], list).tool.doot.locs

    @staticmethod
    def gen_loc_tasks():
        logging.info("Building LocData Auto Tasks: %s", list(DootLocData._all_registered.keys()))
        return TaskGroup(DootLocData._locs_name,
                         {
                             "basename" : "locs::report",
                             "doc"      : ":: Report All Registered Locations",
                             "actions"  : [],
                             "task_dep" : [x for x in DootLocData._all_registered.keys()],
                         },
                         *DootLocData._all_registered.values(),
                         as_creator=True)

    def __init__(self, name="base", **kwargs):
        self._root    : pl.Path() = pl.Path()
        self._postfix             = name
        self._prefix              = DootLocData._locs_name
        self._check_name          = None
        if bool(kwargs):
            self._dir_names       = {x:y for x,y in kwargs.items() if y is not None}
        else:
            self._dir_names       = {x.replace("_",""):x for x in DootLocData._default_locs}
        assert(self.name not in DootLocData._all_registered), self.name
        DootLocData._all_registered[self.name] = self
        self.checker

    def __getattr__(self, val):
        if val in self._dir_names and self._dir_names[val] is not None:
            pathname, postfix = self._calc_postfix(self._dir_names[val])
            return self.root / pathname / postfix

        raise DootDirAbsent(f"{val} is not a location in {self.name}")

    def __contains__(self, val):
        return val in self._dir_names

    def __iter__(self):
        for x,y in self._dir_names.items():
            if y is not None:
                yield (x, getattr(self, x))

    def __str__(self):
        return "  ".join(f"[{x}: ./{y}]" for x,y in self)

    def __repr__(self):
        return f"{self.name} : ({self})"

    def get(self, val):
        return self.__getattr__(val)

    @property
    def name(self):
        return f"{self._prefix}:{self._postfix}"

    def extend(self, *, name=None, **kwargs):
        new_locs = DootLocData(name or self._postfix,
                               **self._dir_names.copy())
        new_locs.update(kwargs)
        return new_locs

    def update(self, extra:dict[str,str|pl.Path]=None, **kwargs):
        if extra is not None:
            self._dir_names.update((x, y) for x,y in extra.items())
        if bool(kwargs):
            self._dir_names.update(kwargs)

        return self

    def auto_subdirs(self, *args):
        for x in self._dir_names:
            match self._dir_names[x]:
                case (val,) if x in args:
                    continue
                case (val,):
                    self._dir_names[x] = val
                case val if x in args:
                    self._dir_names[x] = (val,)
                case _:
                    continue

    def _calc_postfix(self, val) -> tupl(str, str):
        match val:
            case (solo,):
                return (solo, self._postfix or "")
            case _:
                return (val, "")

    @property
    def root(self):
        return self._root

    def move_root(self, new_root:pl.Path):
        self._root = new_root

    @property
    def checker(self) -> str:
        if self._check_name is None:
            self._check_name = CheckDir(self._postfix, dirs=self).name
        return self._check_name

    def _build_task(self):
        task = {
            "name"     : self._postfix,
            "actions"  : [lambda: print(repr(self))],
            "uptodate" : [False],
            "verbosity" : 2,
            "meta" : {
                "checker" : self.checker
            }
        }
        return task
