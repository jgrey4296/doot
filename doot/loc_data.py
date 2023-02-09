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

class LocProxy:

    def __init__(self, locs, val):
        self.locs = locs
        self.val = val

    def __getattr__(self, attr):
        try:
            return LocProxy(self.locs, getattr(self.locs, attr))
        except Exception:
            DootLocData._defaulted.append(f"{attr} = \"{self.val}\"")
            return self

    def __call__(self):
        match self.val:
            case str():
                return self.locs._calc_path(self.val)
            case pl.Path():
                return self.val

class DootLocData:
    """
    Manage locations in a dict-like class, with attribute access,
    that can build tasks for location checks

    `.on_fail` provides a proxy to continue accessing,
    and when `__call__`ed, provides the real value, or a default

    The proxy also reports values that fallback to the default
    to the LocData to then add to `_doot_defaults.toml`
    """

    _all_registered : ClassVar[dict[str, DootLocData]] = {}
    _locs_name  = "_locs::report"

    _defaulted : ClassVar[list[str]] =   []

    @staticmethod
    def set_defaults(config:Tomler):
        DootLocData._default_locs = config.on_fail([], list).tool.doot.locs

    @staticmethod
    def gen_loc_tasks():
        logging.debug("Building LocData Auto Tasks: %s", list(DootLocData._all_registered.keys()))
        return TaskGroup(DootLocData._locs_name,
                         {
                             "basename" : "locs::report",
                             "doc"      : ":: Report All Registered Locations",
                             "actions"  : [],
                             "task_dep" : [x for x in DootLocData._all_registered.keys()],
                         },
                         *DootLocData._all_registered.values(),
                         as_creator=True)

    @staticmethod
    def report_defaulted() -> list[str]:
        return DootLocData._defaulted[:]

    def __init__(self, name="base", files:dict=None, **kwargs):
        self._root    : pl.Path() = pl.Path()
        self._postfix             = name
        self._prefix              = DootLocData._locs_name
        self._check_name          = None
        self._dirs                = {}
        if bool(kwargs):
            self._dirs.update({x:y for x,y in kwargs.items() if y is not None})

        self._files = {x:y for x,y in (files or {}).items() if y is not None}

        intersect = set(self._dirs.keys()) & set(self._files.keys())
        if bool(intersect):
            raise ValueError(f"Directory and File Sets can't intersect: {intersect}")
        if not (self.name not in DootLocData._all_registered):
            raise ValueError(f"Conflicting LocData Name: {self.name}")

        DootLocData._all_registered[self.name] = self
        self.checker

    def __getattr__(self, val):
        match val in self._dirs, val in self._files:
            case True, False:
                target = self._dirs[val]
            case False, True:
                target =  self._files[val]
            case _:
                logging.warning(f"{val} is not a location in {self.name}")
                raise DootDirAbsent(f"{val} is not a location in {self.name}")

        return self._calc_path(target)

    def _calc_path(self, val) -> pl.Path:
        match str(val)[0], val:
            case "/" | "~", _: # absolute path or home
                return pl.Path(val).expanduser()
            case _, (solo,) | [solo]: # with postfix
                return self.root / solo / self._postfix or ""
            case _, _: # normal
                return self.root / val

    def __contains__(self, val):
        return val in self._dirs

    def __iter__(self):
        for x,y in self._dirs.items():
            if y is not None:
                yield (x, getattr(self, x))

    def __str__(self):
        return "  ".join(f"[{x}: ./{y}]" for x,y in self)

    def __repr__(self):
        return f"{self.name} : ({self})"

    def get(self, val):
        return self.__getattr__(val)

    def on_fail(self, val):
        return LocProxy(self, val)

    @property
    def name(self):
        return f"{self._prefix}:{self._postfix}"

    def extend(self, *, name=None, **kwargs):
        new_locs = DootLocData(name or self._postfix,
                               **self._dirs.copy())
        new_locs.update(kwargs)
        return new_locs

    def update(self, extra:dict[str,str|pl.Path]=None, **kwargs):
        if extra is not None:
            self._dirs.update((x, y) for x,y in extra.items() if y is not None)
        if bool(kwargs):
            self._dirs.update((x,y) for x,y in kwargs.items() if y is not None)

        return self

    def auto_subdirs(self, *args):
        for x in self._dirs:
            match self._dirs[x]:
                case (val,) if x in args:
                    continue
                case (val,):
                    self._dirs[x] = val
                case val if x in args:
                    self._dirs[x] = (val,)
                case _:
                    continue

    @property
    def root(self):
        return self._root

    def move_root(self, new_root:pl.Path):
        self._root = new_root

    @property
    def checker(self) -> str:
        if self._check_name is None:
            self._check_name = CheckDir(self._postfix, locs=self).name
        return self._check_name

    def build_report(self):
        max_postfix = max(len(x) for x in DootLocData._all_registered.keys())
        task = {
            "name"     : self._postfix,
            "actions"  : [
                lambda: print(f"{self._postfix:<{max_postfix}} Dirs : {self._dir_str()}"),
                lambda: print(f"{self._postfix:<{max_postfix}} Files: {self._file_str()}") if bool(self._files) else "",
            ],
            "uptodate" : [False],
            "verbosity" : 2,
            "meta" : {
                "checker" : self.checker
            }
        }
        return task

    def _dir_str(self):
        return "  ".join(f"{{{x}: {getattr(self, x)}}}" for x,y in sorted(self._dirs.items()))

    def _file_str(self):
        return " ".join(f"{{{x}: {getattr(self, x)}}}" for x,y in sorted(self._files.items()))


    def ensure(self, *values):
        try:
            for val in values:
                getattr(self, val)
        except AttributeError as err:
            logging.warning("Missing Location Data: %s", val)
            raise err
