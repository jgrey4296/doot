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

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskFlags]


@dataclass
class DootStructuredName:
    """ A Complex name class for identifying tasks and classes.

      Classes are the standard form using in importlib: doot.structs:DootStucturedName
      Tasks use a double colon to separate head from tail name: tasks.globGroup::GlobTask

    """
    head            : list[str]          = field(default_factory=list)
    tail            : list[str]          = field(default_factory=list)

    internal        : bool               = field(default=False, kw_only=True)
    # maybe: tasker : bool               = field(default=False, kw_only=True) -> add '*' at head or tail

    separator       : str                = field(default=doot.constants.TASK_SEP, kw_only=True)
    subseparator    : str                = field(default=".", kw_only=True)

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

    def __hash__(self):
        return hash(str(self))

    def __lt__(self, other) -> bool:
        """ Compare two names, return true if other is a subname of this name
        eg: a.b.c < a.b.c.d
        """
        match other:
            case str():
                other = DootStructuredName.from_str(other)
            case DootStructuredName():
                pass
            case _:
                return False

        for x,y in zip(self.head, other.head):
            if x != y:
                return False

        for x,y in zip(self.tail, other.tail):
            if x != y:
                return False

        return True

    def __contains__(self, other:str):
        return other in str(self)

    def tail_str(self):
        return self.subseparator.join(self.tail)

    def head_str(self):
        return self.subseparator.join(self.head)

@dataclass
class DootCodeReference(DootStructuredName):
    separator : str = field(default=doot.constants.IMPORT_SEP, kw_only=True)

    def try_import(self) -> Any:
        try:
            mod = importlib.import_module(self.module)
            curr = mod
            for name in self.tail:
                curr = getattr(curr, name)

            return curr
        except ModuleNotFoundError as err:
            raise ImportError("Module can't be found", str(self))
        except AttributeError as err:
            raise ImportError("Attempted to import %s but failed", str(self)) from err

    def __str__(self) -> str:
        return "{}{}{}".format(self.module, self.separator, self.value)

    def __hash__(self):
        return hash(str(self))

    @classmethod
    def from_str(cls, name:str):
        if ":" in name:
            groupHead_r, taskHead_r = name.split(":")
            groupHead = groupHead_r.split(".")
            taskHead = taskHead_r.split(".")
        else:
            groupHead = None
            taskHead  = name
        return DootCodeReference(groupHead, taskHead)

    @property
    def module(self):
        return self.subseparator.join(self.head)

    @property
    def value(self):
        return self.subseparator.join(self.tail)

@dataclass
class DootTaskName(DootStructuredName):

    separator  : str = field(default=doot.constants.TASK_SEP, kw_only=True)

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

    def subtask(self, *subtasks, subgroups:list[str]|None=None):
        return DootTaskName(self.head + (subgroups or []),
                                   self.tail + list(subtasks),
                                   internal=self.internal
                                   )

    def __str__(self) -> str:
        return "{}{}{}".format(self.group, self.separator, self.task)

    def __hash__(self):
        return hash(str(self))

    def root(self):
        if self.form in [StructuredNameEnum.CLASS, StructuredNameEnum.CALLABLE]:
            raise TypeError("Getting the root of a class or callable doesn't make sense")
        return f"{self.head_str()}{DootStructuredName.task_separator}{self.tail[0]}"

    @property
    def group(self):
        fmt = "{}"
        if len(self.head) > 1:
            # fmt = "tasks.\"{}\""
            fmt = '"{}"'
        return fmt.format(self.head_str())

    @property
    def task(self):
        return self.tail_str()

    @classmethod
    def from_str(cls, name:str):
        if ":" in name:
            groupHead_r, taskHead_r = name.split("::")
            groupHead = groupHead_r.split(".")
            taskHead = taskHead_r.split(".")
        else:
            groupHead = None
            taskHead  = name
        return DootTaskName(groupHead, taskHead)
