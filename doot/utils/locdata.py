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

from doot.utils.task_group import TaskGroup
from doot.utils.checkdir import CheckDir
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

@dataclass
class DootLocData:
    """

    """

    prefix   : None | str = field()
    _build   : str        = field(default="build")
    _src     : str        = field(default="src")
    _codegen : str        = field(default="_codegen")
    _temp    : str        = field(default=".temp")
    _docs    : str        = field(default="docs")
    _data    : str        = field(default="data")
    _logs    : str        = field(default="logs")

    _root    : pl.Path()            = field(init=False, default_factory=pl.Path)
    extra    : dict["str", pl.Path] = field(init=False, default_factory=dict)

    all_loc_groups : ClassVar[list[DootLocData]] = []

    @staticmethod
    def gen_loc_tasks():
        tasks = [x._build_task() for x in DootLocData.all_loc_groups]
        return TaskGroup("dir report group", *tasks)

    def __post_init__(self):
        # self.create_doit_tasks = self._build_task
        self.build_checks()
        DootLocData.all_loc_groups.append(self)

    def get_val_postfix(self, val) -> tupl(str, str):
        if isinstance(val, tuple) and len(val) == 1:
            return (val[0], "")
        return (val, self.prefix or "")

    def add_extra(self, extra:dict[str,str|pl.Path]):
        self.extra.update((x, pl.Path(y)) for x,y in extra.items())

    ##-- outputs
    @property
    def root(self):
        return self._root

    @property
    def build(self) -> pl.Path:
        """ where final outputs are put """
        if self._build is None:
            raise DootDirAbsent(f"No Build dir in {self.prefix}")

        val, post = self.get_val_postfix(self._build)
        return self._root / val / post

    @property
    def codegen(self) -> pl.Path:
        if self._codegen is None:
            raise DootDirAbsent(f"No Codegen dir in {self.prefix}")

        val, _ = self.get_val_postfix(self._codegen)
        return self.src / val

    @property
    def temp(self) -> pl.Path:
        if self._temp is None:
            raise DootDirAbsent(f"No Temp dir in {self.prefix}")

        val, post = self.get_val_postfix(self._temp)
        return self._root / val / post

    @property
    def logs(self) -> pl.Path:
        if self._logs is None:
            raise DootDirAbsent(f"No Log dir in {self.prefix}")

        tmp, _ = self.get_val_postfix(self._temp)
        logs, post = self.get_val_postfix(self._logs)
        return self._root / tmp / logs / post

    ##-- end outputs

    ##-- inputs
    @property
    def src(self) -> pl.Path:
        if self._src is None:
            raise DootDirAbsent(f"No Src dir in {self.prefix}")

        return self._root / self._src

    @property
    def data(self) -> pl.Path:
        if self._data is None:
            raise DootDirAbsent(f"No Data dir in {self.prefix}")

        val, post = self.get_val_postfix(self._data)
        return self._root / val / post

    @property
    def docs(self) -> pl.Path:
        if self._docs is None:
            raise DootDirAbsent(f"No Docs dir in {self.prefix}")

        val, post = self.get_val_postfix(self._docs)
        return self._root / val / post

    ##-- end inputs

    @property
    def checker(self) -> str:
        prefix = self.prefix or "base"
        return f"_checkdir::{prefix}"

    def build_checks(self):
        CheckDir.register(self.prefix or "base", [y for x,y in list(self)])

    def __iter__(self):
        result = []
        for x in ["build", "temp", "src", "codegen", "docs", "data"]:
            try:
                result.append((x, getattr(self, x)))
            except DootDirAbsent:
                continue
        result += self.extra.items()
        return iter(result)


    def __str__(self):
        paths  = "  ".join(f"[{x}: ./{y}]" for x,y in self)
        return f"** {paths}"


    def _build_task(self):
        task = {
            "basename" : "doot::dirs",
            "name"     : self.prefix or "base",
            "actions"  : [lambda: print(str(self))],
            "verbosity" : 2,
        }
        return task

    def extend(self, **kwargs):
        return replace(self, **kwargs)
