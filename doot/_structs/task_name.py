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
import doot
import doot.errors
from doot.enums import TaskFlags, ReportEnum
from doot._structs.structured_name import StructuredName, aware_splitter

TaskFlagNames : Final[str] = [x.name for x in TaskFlags]

@dataclass(eq=False, slots=True)
class DootTaskName(StructuredName):
    """
      A Task Name.

    """

    separator          : str                     = field(default=doot.constants.patterns.TASK_SEP, kw_only=True)
    version_constraint : None|str                = field(default=None)
    meta               : TaskFlags               = field(default=TaskFlags.default)
    args               : dict                    = field(default_factory=dict)

    @classmethod
    def build(cls, name:str|dict|DootTaskName, *, args=None):
        """ build a name from the various ways it can be specificed.
          handles a single string of the group and taskname,
          or a dict that specifies taskname and maybe the groupname

        """
        groupHead = []
        taskHead  = []
        match name:
            case DootTaskName():
                return name
            case str() if doot.constants.patterns.TASK_SEP in name:
                try:
                    groupHead_r, taskHead_r = name.split(doot.constants.patterns.TASK_SEP)
                    groupHead = groupHead_r.split(".")
                    taskHead = taskHead_r.split(".")
                except ValueError:
                    raise doot.errors.DootConfigError("Provided Task Name can't be split correctly, check it is of the form group::name", name)
            case str():
                groupHead.append("default")
                taskHead.append(name)
            case {"name": str() as name} if doot.constants.patterns.TASK_SEP in name:
                try:
                    groupHead_r, taskHead_r = name.split(doot.constants.patterns.TASK_SEP)
                    groupHead = groupHead_r.split(".")
                    taskHead = taskHead_r.split(".")
                except ValueError:
                    raise doot.errors.DootConfigError("Provided Task Name can't be split correctly, check it is of the form group::name", name)
            case { "group": str() as group, "name": str() as name }:
                groupHead.append(group)
                taskHead.append(name)
            case {"name": str() as name}:
                groupHead.append("default")
                taskHead.append(name)
            case {"name": DootTaskName() as name}:
                return name
            case _:
                raise doot.errors.DootError("Unrecognized name format: %s", name)


        return DootTaskName(groupHead, taskHead, args=args)

    def __post_init__(self):
        sub_split = ftz.partial(aware_splitter, sep=self.subseparator)
        match self.head:
            case ["tasks", x] if x.startswith('"') and x.endswith('"'):
                self.head = ftz.reduce(lambda x, y: x + y, map(aware_splitter, x[1:-1]))
            case ["tasks", *xs]:
                self.head = ftz.reduce(lambda x, y: x + y, map(aware_splitter, xs))
            case list():
                self.head = ftz.reduce(lambda x, y: x + y, map(aware_splitter, self.head))
            case str():
                self.head = self.head.split(self.subseparator)
            case None | []:
                self.head = ["default"]

        match self.tail:
            case list():
                self.tail = ftz.reduce(lambda x, y: x + y, map(aware_splitter, self.tail))
            case str():
                self.tail = self.tail.split(self.subseparator)
            case None | []:
                self.tail = ["default"]

        if self.tail[0].startswith(doot.constants.patterns.INTERNAL_TASK_PREFIX):
            self.meta |= TaskFlags.INTERNAL

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
        return self.subseparator.join([str(x) if not isinstance(x, UUID) else "${}$".format(x.hex) for x in self.tail])

    @property
    def readable(self):
        group = self.group
        tail = self.subseparator.join([str(x) if not isinstance(x, UUID) else "<UUID>" for x in self.tail])
        return "{}{}{}".format(group, self.separator, tail)

    def root(self) -> DootTaskName:
        return DootTaskName.build(f"{self.head_str()}{self.separator}{self.tail[0]}")

    def task_head(self) -> DootTaskName:
        if self.tail[-1] == doot.constants.patterns.SUBTASKED_HEAD:
            return self

        return self.subtask(doot.constants.patterns.SUBTASKED_HEAD)

    def subtask(self, *subtasks, subgroups:list[str]|None=None) -> DootTaskName:
        args = self.args.copy() if self.args else None
        subs = []
        match [x for x in subtasks if x != None]:
            case [int() as i, DootTaskName() as x]:
                subs.append(str(i))
                subs.append(x.task.removeprefix(self.task + "."))
            case [str() as x]:
                subs.append(x)
            case [*xs]:
                subs = xs

        return DootTaskName(self.head + (subgroups or []),
                            self.tail + subs,
                            meta=self.meta,
                            args=args)

    def specialize(self, *, info=None):
        match info:
            case None:
                return self.subtask(doot.constants.patterns.SPECIALIZED_ADD, uuid1())
            case _:
                return self.subtask(doot.constants.patterns.SPECIALIZED_ADD, info, uuid1())

    def last(self):
        return self.tail[-1]
