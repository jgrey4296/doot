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
printer = logmod.getLogger("doot._printer")

from tomlguard import TomlGuard
import doot
import doot.errors
from doot._abstract import Job_i
from doot.structs import DootCodeReference, DootTaskSpec, DootTaskName, DootKey
from doot.mixins.job.walker import WalkerMixin

class TaskLimitMixin:
    """
      Limit the number of task the job generates
    """

    def __init__(self, spec):
        super().__init__(spec)
        match self.spec.extra.on_fail("identity", str).early_select_fn():
            case "identity":
                self.early_select_fn = self._identity_select
            case str() as s:
                ref = DootCodeReference.from_str(s)
                self.early_select_fn = ref.try_import()

        match self.spec.extra.on_fail("hard", str).select_limit_type().lower():
            case "hard":
                self.limit_type = "hard"
            case "soft":
                self.limit_type = "soft"
            case x:
                raise doot.errors.DootConfigError("Bad select_limit_type value", str(self.spec.name), x)

        self.select_limit = self.spec.extra.on_fail((None,), None|int).select_limit()
        match self.select_limit:
            case None:
                pass
            case x if x < 1:
                raise doot.errors.DootTaskError("Can't subselect a non-positive amount")

        match self.spec.extra.on_fail("all", str).late_select_fn():
            case "all" | "All":
                self.late_select_fn = self._select_all
            case "random" | "Random":
                self.late_select_fn = self._random_select
            case str() as s:
                ref = DootCodeReference.from_str(s)
                self.late_select_fn = ref.try_import()

    def _build_subs(self) -> Generator[DootTaskSpec]:
        logging.debug("%s : Building Subselection Walker SubTasks", self.name)

        selected = []
        for task in super()._build_subs():
            match task:
                case None:
                    pass
                case DootTaskSpec() as sub if self.early_select_fn(self, sub):
                    selected.append(sub)

        filtered = self.late_select_fn(self, selected)
        self.total_subtasks = len(filtered)

        match self.limit_type, self.select_limit, self.total_subtasks:
            case _, None, _:
                pass
            case "hard", lim, total if lim <= total:
                raise doot.errors.DootTaskError("Job broke its subtask limit", str(self.spec.name), self.select_limit, self.total_subtasks)
            case "soft", lim, total if lim <= total:
                logging.debug("Soft Limiting Job: %s : (limit %s) < (generated %s))", str(self.spec.name), lim, total)
                filtered = filtered[:lim]
            case _:
                pass

        for task in filtered:
            yield task


    @staticmethod
    def _identity_select(job:Job_i, spec:DootTaskSpec) -> bool:
        return True

    @staticmethod
    def _random_select(job:Job_i, specs:list[DootTaskSpec]) -> list[DootTaskSpec]:
        return random.sample(specs, match_amnt)

    @staticmethod
    def _select_all(job:Job_i, specs:list[DootTaskSpec]) -> list[DootTaskSpec]:
        return specs

    @classmethod
    def stub_class(cls, stub):
        stub['early_select_fn'].set(type="callable",    default="identity", priority=100, comment=" : [job, spec] -> bool")
        stub['late_select_fn'].set(type="callable",    default="all", priority=100, comment=" : [job, list[spec]] -> list[spec]. (all, random, or coderef)")

        stub['select_limit_type'].set(type="str", default="hard", priority=100, comment="hard | soft")
        stub['select_limit'].set(type="int|None", default="5", priority=100, prefix="# ")
