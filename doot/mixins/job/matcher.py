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
from doot.mixins.job.expander import WalkExpander_M

class PatternMatcher_M:
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
        """ an identity matcher that returns the tasks current ctor """
        return task.ctor


    @staticmethod
    def _match_ext(job, task):
        """ a matcher which maps extra.fpath.ext -> ctor """
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

        printer.info("Matched %s (%s) to: %s", task.name, task.extra[match_field].name, ctor)
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

        if 'sub_task' in stub.parts:
            del stub.parts["sub_task"]
