#!/usr/bin/env python3
"""


See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import doot
import doot.errors
from doot.structs import DootCodeReference
from doot.mixins.tasker.walker import WalkerMixin

class SubSelectMixin(WalkerMixin):
    """

    """

    def __init__(self, spec):
        super().__init__(spec)
        self.filter_fn  = self.spec.extra.on_fail("null:fn").filter_fn(wrapper=DootCodeReference.from_str)
        self.select_fn  = self.spec.extra.on_fail("null:fn").sect_fn(wrapper=DootCodeReference.from_str)

    def _build_subs(self) -> Generator[DootTaskSpec]:
        logging.debug("%s : Building Subselection Walker SubTasks", self.name)
        self.total_subtasks = 0
        # Find
        matching   = list(self.walk_all(fn=self.filter_fn))

        # Select
        match self.spec.extra.on_fail("random", str).select_method():
            case "random":
                match_amnt = self.spec.extra.on_fail(1, int).select_num(int)
                if match_amnt < 1:
                    raise doot.errors.DootTaskError("Can't subselect a non-positive amount")
                subselection = random.sample(matching, match_amnt)
            case "fn":
                if self.select_fn is None:
                    raise doot.errors.DootTaskError("Subselect specified a fn, but no function was loaded")
                subselection = self.select_fn(matching)
            case _:
                raise doot.errors.DootTaskError("Bad Select Method specified")

        # Build
        for i, (uname, fpath) in enumerate(subselection):
            match self._build_subtask(i, uname, fpath=fpath, fstem=fpath.stem, fname=fpath.name, lpath=self.rel_path(fpath)):
                case None:
                    pass
                case DootTaskSpec() as subtask:
                    self.total_subtasks += 1
                    yield subtask
                case _ as subtask:
                    raise TypeError("Unexpected type for subtask: %s", type(subtask))


    @classmethod
    def stub_class(cls, stub):
        stub['select_num'].set(type="int",    default=1,        priority=100)
        stub['select_method'].set(type="str", default="random", priority=100)
        stub['select_fn'].set(type="str",     prefix="# ",      priority=100)


class PatternMatcherMixin(WalkerMixin):
    """

    """

    def __init__(self, spec:DootTaskSpec):
        super().__init__(spec)

    def _build_subs(self) -> Generator[DootTaskSpec]:
        self.total_subtasks = 0
        logging.debug("%s : Building Walker SubTasks", self.name)
        filter_fn = self.import_class(self.spec.extra.on_fail((None,)).filter_fn())
        for i, (uname, fpath) in enumerate(self.walk_all(fn=filter_fn)):
            match self._build_subtask(i, uname, fpath=fpath, fstem=fpath.stem, fname=fpath.name, lpath=self.rel_path(fpath)):
                case None:
                    pass
                case DootTaskSpec() as subtask:
                    self.total_subtasks += 1
                    yield subtask
                case _ as subtask:
                    raise TypeError("Unexpected type for subtask: %s", type(subtask))

    def specialize_subtask(self, task) -> None|dict|DootTaskSpec:
        # lookup using spec keys
        return task

    @classmethod
    def stub_class(cls, stub):
        pass
