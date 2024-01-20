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
        stub['early_select_fn'].set(type="callable",    default="identity", priority=100, comment=" : Callable[[job, spec], bool]")
        stub['late_select_fn'].set(type="callable",    default="all", priority=100, comment=" : Callable[[job, list[spec]], list[spec]. all, random, or coderef")

        stub['select_limit_type'].set(type="str", default="hard", priority=100, comment="hard | soft")
        stub['select_limit'].set(type="int|None", default="5", priority=100, prefix="# ")

class PatternMatcherMixin:
    """
      pattern match on generated specs to set their task ctor,
      instead of a static "subtask" field
      eg: [task1(fpath="blah.bib"), task2("bloo.json")]
      task1.ctor = bib::task
      task2.ctor = json::task
    """

    def __init__(self, spec:DootTaskSpec):
        super().__init__(spec)
        match spec.extra.on_fail("identity", str).match_fn():
            case "identity":
                self.match_fn = self._identity_match
            case "ext":
                self.match_fn = self._match_ext
            case str() as x:
                ref = DootCodeReference.from_str(x)
                self.match_fn = ref.try_import()

    def _build_subs(self) -> Generator[DootTaskSpec]:
        logging.debug("%s : Building Walker SubTasks", self.name)
        for task in super()._build_subs():
            match task:
                case None:
                    pass
                case DootTaskSpec():
                    # match spec -> spec here
                    task.ctor = self.match_fn(self, task)
                    yield task

    @staticmethod
    def _identity_match(job, task) -> DootTaskName:
        return task.ctor


    @staticmethod
    def _match_ext(job, task):
        ctor        = None
        mapping     = job.spec.extra.on_fail({}, dict|TomlGuard).match_map()
        match_field = job.spec.extra.on_fail("fpath", str).match_field()
        match task.extra.on_fail(None)[match_field]():
            case str() as val:
                key  = DootKey.match(val, explicit=True)
                path = key.to_path(None, task.state)
                ext  = path.suffix
                ctor = mapping.get(ext, None)
            case pl.Path() as path:
                ext  = path.suffix
                ctor = mapping.get(ext, None)

        match ctor:
            case str():
                return DootTaskName.from_str(ctor)
            case DootTaskName():
                return ctor
            case DootCodeReference():
                raise doot.errors.DootTaskError("Pattern match found a coderef", str(task.name), match_field, ctor)
            case _:
                raise doot.errors.DootTaskError("Pattern Match failed for task", str(task.name), match_field)

    @classmethod
    def stub_class(cls, stub):
        stub['match_fn'].set(type="callable", default="identity", priority=100, comment=" : Callable[[job, spec], TaskName]. identity|ext|coderef")
        stub['match_map'].set(type="dict", default={}, priority=100, prefix="# ", comment="map str -> TaskName")
        stub['match_field'].set(type="str", default="fpath", priority=100, prefix="# ", comment="The task state field to use for mapping")
