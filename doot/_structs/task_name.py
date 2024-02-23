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
from dataclasses import InitVar, dataclass, field
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

import importlib
from tomlguard import TomlGuard
import doot.errors
import doot.constants
from doot.enums import TaskFlags, ReportEnum
from doot._structs.structured_name import DootStructuredName

TaskFlagNames : Final[str] = [x.name for x in TaskFlags]

@dataclass(eq=False, slots=True)
class DootTaskName(DootStructuredName):
    """
      A Task Name.
    """

    internal           : bool                    = field(default=False, kw_only=True)
    separator          : str                     = field(default=doot.constants.TASK_SEP, kw_only=True)
    version_constraint : None|str                = field(default=None)
    args               : dict                    = field(default_factory=dict)

    @classmethod
    def from_str(cls, name:str, *, args=None):
        if ":" in name:
            try:
                groupHead_r, taskHead_r = name.split("::")
                groupHead = groupHead_r.split(".")
                taskHead = taskHead_r.split(".")
            except ValueError:
                raise doot.errors.DootConfigError("Provided Task Name can't be split correctly, check it is of the form group::name", name)
        else:
            groupHead = None
            taskHead  = name
        return DootTaskName(groupHead, taskHead, args=args)

    def __post_init__(self):
        match self.head:
            case ["tasks", x] if x.startswith('"') and x.endswith('"'):
                self.head = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(self.subseparator), x[1:-1]))
            case ["tasks", *xs]:
                self.head = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(self.subseparator), xs))
            case list():
                self.head = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(self.subseparator), self.head))
            case str():
                self.head = self.head.split(self.subseparator)
            case None | []:
                self.head = ["default"]

        match self.tail:
            case list():
                self.tail = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(self.subseparator), self.tail))
            case str():
                self.tail = self.tail.split(self.subseparator)
            case None | []:
                self.tail = ["default"]

        self.internal = self.tail[0].startswith(doot.constants.INTERNAL_TASK_PREFIX) or self.internal

    def __str__(self) -> str:
        return "{}{}{}".format(self.group, self.separator, self.task)

    def __repr__(self) -> str:
        name = str(self)
        return f"<TaskName: {name}>"

    def __hash__(self):
        return hash(str(self))

    def __contains__(self, other) -> bool:
        match other:
            case str():
                return other in str(self)
            case DootTaskName() if not other.version_constraint:
                return str(self) in str(other)
            case DootTaskName():
                self_vc  = self.version_constraint
                other_vc = other.version_constraint
                # check < | <= | > | >= | != | =
                # of self_vc to other_vc
                raise NotImplementedError()

    @property
    def group(self) -> str:
        fmt = "{}"
        if len(self.head) > 1:
            # fmt = "tasks.\"{}\""
            fmt = '"{}"'
        return fmt.format(self.head_str())

    @property
    def task(self) -> str:
        return self.tail_str()

    def root(self):
        return f"{self.head_str()}{self.separator}{self.tail[0]}"

    def subtask(self, *subtasks, subgroups:list[str]|None=None) -> DootTaskName:
        args = self.args.copy() if self.args else None
        subs = []
        match subtasks:
            case [int() as i, DootTaskName() as x]:
                subs.append(str(i))
                subs.append(x.task.removeprefix(self.task + "."))
            case [str() as x]:
                subs.append(x)
            case [*xs]:
                subs = [str(x) for x in xs]

        return DootTaskName(self.head + (subgroups or []),
                            self.tail + subs,
                            internal=self.internal,
                            args=args)

    def specialize(self, *, info=None):
        match info:
            case None:
                return self.subtask(doot.constants.SPECIALIZED_ADD, "${}$".format(uuid1().hex))
            case _:
                return self.subtask(doot.constants.SPECIALIZED_ADD, info, "${}$".format(uuid1().hex))
