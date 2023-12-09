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
from doot.enums import TaskFlags, ReportEnum, StructuredNameEnum

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskFlags]


@dataclass
class DootStructuredName:
    """ A Complex name class for identifying tasks and classes.

      Classes are the standard form using in importlib: doot.structs:DootStucturedName
      Tasks use a double colon to separate group from task name: tasks.globGroup::GlobTask

    """
    group           : list[str]          = field(default_factory=list)
    task            : list[str]          = field(default_factory=list)

    internal        : bool               = field(default=False, kw_only=True)
    # maybe: tasker : bool               = field(default=False, kw_only=True) -> add '*' at head or tail

    form            : StructuredNameEnum = field(default=StructuredNameEnum.TASK, kw_only=True)
    task_separator  : ClassVar[str] = doot.constants.TASK_SEP

    class_separator : ClassVar[str] = doot.constants.IMPORT_SEP
    subseparator    : ClassVar[str] = "."

    def __post_init__(self):
        match self.group:
            case ["tasks", x] if x.startswith('"') and x.endswith('"'):
                self.group = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(DootStructuredName.subseparator), x[1:-1]))
            case ["tasks", *xs]:
                self.group = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(DootStructuredName.subseparator), xs))
            case list():
                self.group = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(DootStructuredName.subseparator), self.group))
            case str():
                self.group = self.group.split(DootStructuredName.subseparator)
            case None | []:
                self.group = ["default"]

        match self.task:
            case list():
                self.task = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(DootStructuredName.subseparator), self.task))
            case str():
                self.task = self.task.split(DootStructuredName.subseparator)
            case None | []:
                self.task = ["default"]

        self.internal = self.task[0].startswith(doot.constants.INTERNAL_TASK_PREFIX) or self.internal

    def __str__(self) -> str:
        sep = DootStructuredName.task_separator if self.form is StructuredNameEnum.TASK else DootStructuredName.class_separator
        return "{}{}{}".format(self.group_str(), sep, self.task_str())

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

        for x,y in zip(self.group, other.group):
            if x != y:
                return False

        for x,y in zip(self.task, other.task):
            if x != y:
                return False

        return True

    def __contains__(self, other:str):
        return other in str(self)

    def task_str(self):
        return DootStructuredName.subseparator.join(self.task)

    def group_str(self):
        fmt = "{}"
        match self.form:
            case StructuredNameEnum.TASK if len(self.group) > 1:
                # fmt = "tasks.\"{}\""
                fmt = '"{}"'
            case StructuredNameEnum.TASK:
                # fmt = "tasks.{}"
                fmt = "{}"
            case StructuredNameEnum.CLASS | StructuredNameEnum.CALLABLE:
                fmt = "{}"

        base = DootStructuredName.subseparator.join(self.group)
        return fmt.format(base)

    def subtask(self, *subtasks, subgroups:list[str]|None=None):
        return DootStructuredName(self.group + (subgroups or []),
                                   self.task + list(subtasks),
                                   internal=self.internal
                                   )


    def root(self):
        if self.form in [StructuredNameEnum.CLASS, StructuredNameEnum.CALLABLE]:
            raise TypeError("Getting the root of a class or callable doesn't make sense")
        return f"{self.group_str()}{DootStructuredName.task_separator}{self.task[0]}"

    @staticmethod
    def from_str(name:str, form:StructuredNameEnum=StructuredNameEnum.TASK):
        sep = DootStructuredName.task_separator if form is StructuredNameEnum.TASK else DootStructuredName.class_separator
        if sep in name:
            groupHead_r, taskHead_r = name.split(sep)
            groupHead = groupHead_r.split(DootStructuredName.subseparator)
            taskHead = taskHead_r.split(DootStructuredName.subseparator)
        else:
            groupHead = None
            taskHead  = name
        return DootStructuredName(groupHead, taskHead, form=form)

    def try_import(self) -> Any:
        try:
            mod = importlib.import_module(self.group_str())
            curr = mod
            for name in self.task:
                curr = getattr(curr, name)

            return curr
        except AttributeError as err:
            raise ImportError("Attempted to import %s but failed", str(self)) from err



"""


"""
