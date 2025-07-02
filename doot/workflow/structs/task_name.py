#!/usr/bin/env python3
"""

"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import weakref
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from pydantic import field_validator, model_validator
from jgdv import Maybe, Proto
from jgdv.structs.strang import Strang
from jgdv.structs.strang import _interface as StrangAPI  # noqa: N812
from jgdv.structs.strang.processor import StrangBasicProcessor

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors

# ##-- end 1st party imports

from .. import _interface as API # noqa: N812

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv._abstract.pre_processable import PreProcessResult, PostInstanceData, InstanceData
    from jgdv import Maybe, VerStr
    from jgdv.structs.strang import Strang_p
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from .._interface import TaskName_p
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging
DEFAULT_SEP   : Final[str] = doot.constants.patterns.TASK_SEP # type: ignore[attr-defined]
TASKS_PREFIX  : Final[str] = "tasks."

##--|

class TaskNameHeadMarks_e(StrangAPI.StrangMarkAbstract_e):
    """ Markers used in a Strang's head """
    basic = "$basic$"

class TaskNameBodyMarks_e(StrangAPI.StrangMarkAbstract_e):
    """ Markers Used in a base Strang's body """

    head        = "$head$"
    cleanup     = "$cleanup$"
    partial     = "$partial$"
    data        = "$data$"
    empty       = ""
    hide        = "_"
    extend      = "+"
    customised  = "$+$"

    @override
    @classmethod
    def default(cls) -> Maybe[str]:
        """ The mark used if no mark is found"""
        return None

    @override
    @classmethod
    def implicit(cls) -> set[str]:
        """ Marks that arent in the form $mark$ """
        return {cls.hide, cls.empty}

    @override
    @classmethod
    def skip(cls) -> Maybe[str]:
        """ The mark placed in empty words """
        return cls.empty

    @override
    @classmethod
    def idempotent(cls) -> set[str]:
        """ marks you can't have more than one of """
        return {cls.head, cls.hide}


    @classmethod
    def generated(cls) -> set[str]:
        return { cls.cleanup, cls.head }
##--|
TASKSECTIONS : Final[StrangAPI.Sections_d] = StrangAPI.Sections_d(
    StrangAPI.Sec_d("group", ".", "::", str, TaskNameHeadMarks_e, True),  # noqa: FBT003
    StrangAPI.Sec_d("body",  ".", None, str, TaskNameBodyMarks_e, True),  # noqa: FBT003
)
##--|

class TaskNameProcessor[T:API.TaskName_p](StrangBasicProcessor):

    @override
    def pre_process(self, cls:type[T], input:Any, *args:Any, strict:bool=False, **kwargs:Any) -> PreProcessResult:
        """ Remove 'tasks' as a prefix, and strip quotes  """
        match input:
            case Strang():
                cleaned = str(input).removeprefix(TASKS_PREFIX).replace('"', "")
            case str():
                cleaned = input.removeprefix(TASKS_PREFIX).replace('"', "")
            case x if not strict:
                cleaned = str(x)
            case x:
                raise TypeError(type(x))

        return super().pre_process(cls, cleaned, *args, strict=strict, **kwargs)

    @override
    def _implicit_mark(self, val:str, *, sec:StrangAPI.Sec_d, data:dict, index:int, maxcount:int) -> Maybe[StrangAPI.StrangMarkAbstract_e]:
        """ Builds certain marks that are not in the form $mark$.

        In particular, pass marks that are empty words between two case chars: group::a.b..c
        And meta marks for tasks like job and hide: group::+._.a.b.c
        """
        match sec.marks:
            case None:
                return None
            case x:
                marks = x
        match marks.skip():
            case None:
                pass
            case x if val == x.value:
                return x

        if val not in marks:
            return None
        return marks(val)

@Proto(API.TaskName_p, StrangAPI.Strang_p)
class TaskName(Strang):
    """
      A Task Name.
    """
    __slots__              = ()
    Marks      : ClassVar  = TaskNameBodyMarks_e
    _processor : ClassVar  = TaskNameProcessor()
    _sections  : ClassVar  = TASKSECTIONS

    def with_cleanup(self) -> Self:
        """
        Generate a $cleanup$ task name. the UUID of the source is carried with it
        """
        if self.is_cleanup():
            return self
        if not self.uuid():
            raise ValueError("adding $cleanup$ to a task name requires a uuid in the base", self[:])

        return self.push(TaskNameBodyMarks_e.cleanup, uuid=self.uuid())

    def with_head(self) -> Self:
        """ generate a $head$ task name, carrying the uuid along with it """
        if self.is_head():
            return self
        if not self.uuid():
            raise ValueError("Adding $head$ to a task name requires a uuid in the base", self[:])

        return self.push(TaskNameBodyMarks_e.head, uuid=self.uuid())

    def is_cleanup(self) -> bool:
        return TaskNameBodyMarks_e.cleanup in self

    def is_head(self) -> bool:
        return TaskNameBodyMarks_e.head in self

    def pop_generated(self) -> Self:
        if not (self.is_head() or self.is_cleanup()):
            return self

        assert(self.uuid())
        base = self.pop(top=False)
        return type(self)(f"{base}[<uuid>]", uuid=self.uuid())
