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
                    Iterable, Iterator, Mapping, Match, MutableMapping, Self,
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

from pydantic import field_validator, model_validator
import importlib
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.enums import TaskFlags, ReportEnum
from doot._structs.structured_name import StructuredName, aware_splitter, TailEntry

class TaskName(StructuredName):
    """
      A Task Name.
      Infers metadata(TaskFlags) from the string data it is made of.
      a trailing '+' in the head makes it a job
      a leading '_' in the tail makes it an internal name, eg: group::_.task
      having a '$gen$' makes it a concrete name
      having a '$head$' makes it a job head
      Two separators in a row marks a recall point for root()

      TODO: parameters

    """

    meta                : TaskFlags               = TaskFlags.default
    args                : dict                    = {}
    version_constraint  : None|str                = None

    _roots              : tuple[int, int]         = (-1,-1)

    _separator          : ClassVar[str]           = doot.constants.patterns.TASK_SEP
    _gen_marker         : ClassVar[str]           = doot.constants.patterns.SPECIALIZED_ADD
    _internal_marker    : ClassVar[str]           = doot.constants.patterns.INTERNAL_TASK_PREFIX
    _head_marker        : ClassVar[str]           = doot.constants.patterns.SUBTASKED_HEAD
    _job_marker         : ClassVar[str]           = "+" # TODO move to constants.toml
    _root_marker        : ClassVar[str]           = ""  # TODO move to constants.toml

    @classmethod
    def build(cls, name:str|dict|TaskName, *, args=None):
        """ build a name from the various ways it can be specificed.
          handles a single string of the group and taskname,
          or a dict that specifies taskname and maybe the groupname

        """
        match name:
            case TaskName():
                return name
            case str() if cls._separator not in name:
                raise ValueError("TaskName has no group", name)
            case str():
                group, task = name.split(doot.constants.patterns.TASK_SEP)
            case {"name": TaskName() as name}:
                return name
            case {"name": str() as name} if cls._separator not in name:
                raise ValueError("TaskName has no group", name)
            case {"name": str() as name}:
                group , task = name.split(doot.constants.patterns.TASK_SEP)
            case { "group": str() as group, "name": str() as task}:
                pass
            case _:
                raise ValueError("Unrecognized name format: %s", name)

        return TaskName(head=[group], tail=[task], args=args or {})

    @field_validator("head", mode="before")
    def _process_head(cls, head):
        """ ensure the head is in its component parts """
        match head:
            case list():
                head = [x.replace('"',"").replace("'","") for x in head]
                head = ftz.reduce(lambda x, y: x + y, map(aware_splitter, head))
            case _:
                raise ValueError("Bad Task Head Value", head)

        match head:
            case ["tasks", *xs]:
                return xs
            case _:
                 return head

    @field_validator("tail", mode="before")
    def _process_tail(cls, tail):
        """ ensure the tail is in its component parts """
        match tail:
            case list():
                tail = ftz.reduce(lambda x, y: x + y, map(aware_splitter, tail))
            case str():
                tail = tail.split(cls._subseparator)
            case None | []:
                tail = ["default"]
            case _:
                raise ValueError("Bad Task Tail Value", tail)

        root_set = {TaskName._root_marker}
        filtered = [x for x,y in zip(tail, itz.chain(tail[1:], [None])) if {x,y} != root_set ]
        return filtered

    @model_validator(mode="after")
    def check_metdata(self) -> Self:
        if self.head[-1] == TaskName._job_marker:
            self.meta |= TaskFlags.JOB
        if self.tail[0] == TaskName._internal_marker:
            self.meta |= TaskFlags.INTERNAL
        if TaskName._gen_marker in self.tail:
            self.meta |= TaskFlags.CONCRETE
        if TaskName._head_marker in self.tail:
            self.meta |= TaskFlags.JOB_HEAD
            self.meta &= ~TaskFlags.JOB

        if TaskFlags.CONCRETE in self.meta and 'uuid' not in self.args:
            raise ValueError("Instanced Name lacks a stored uuid", self)
        if TaskFlags.CONCRETE in self.meta and TaskName._gen_marker not in self.tail:
            raise ValueError("Specialized Name lacks the specialized keyword in its tail", self)
        if TaskFlags.INTERNAL in self.meta and not self.tail[0] == TaskName._internal_marker:
            raise ValueError("Internal Name lacks a prefix underscore", self)

        return self
    @model_validator(mode="after")
    def _process_roots(self) -> Self:
        # filter out double root markers
        indices = [i for i,x in enumerate(self.tail[:-1]) if x == TaskName._root_marker]
        if bool(indices):
            min_i, max_i = min(indices), max(indices)
            self._roots = (min_i, max_i)
        return self

    def __str__(self) -> str:
        return "{}{}{}".format(self.group, self._separator, self.task)

    def __repr__(self) -> str:
        name = str(self)
        return f"<TaskName: {name}>"

    def __hash__(self):
        return hash(str(self))

    def __contains__(self, other):
        match other:
            case TaskFlags():
                return other in self.meta
            case _:
                return super().__contains__(other)

    @ftz.cached_property
    def group(self) -> str:
        fmt = "{}"
        if len(self.head) > 1:
            # fmt = "tasks.\"{}\""
            fmt = '"{}"'
        return fmt.format(self.head_str())

    @ftz.cached_property
    def task(self) -> str:
        return self._subseparator.join([str(x) if not isinstance(x, UUID) else "${}$".format(hex(x.time_low)) for x in self.tail])

    @ftz.cached_property
    def readable(self):
        group = self.group
        tail = self._subseparator.join([str(x) if not isinstance(x, UUID) else "<UUID>" for x in self.tail])
        return "{}{}{}".format(group, self._separator, tail)

    def is_instance(self) -> bool:
        return TaskFlags.CONCRETE in self.meta

    def match_version(self, other) -> bool:
        """ match version constraints of two task names against each other """
        raise NotImplementedError()

    def root(self, *, top=False) -> TaskName:
        """
        Strip off detail information to get the basic task name for id purposes
        """
        match self._roots:
            case [-1, -1]:
                return self
            case [x, _] if top:
                return TaskName(head=self.head[:], tail=self.tail[:x])
            case [_, x]:
                return TaskName(head=self.head[:], tail=self.tail[:x])

    def add_root(self) -> TaskName:
        """ Add a root marker if the last element isn't already a root marker """
        match self.last():
            case x if x == TaskName._root_marker:
                return self
            case _:
                return self.subtask()

    def subtask(self, *subtasks, subgroups:list[str]|None=None, **kwargs) -> TaskName:
        """ generate an extended name, with more information
        eg: a.group::simple.task
        ->  a.group::simple.task..targeting.something

        propagates args
        adds a root marker to recover the original
        """

        args = self.args.copy() if self.args else {}
        if bool(kwargs):
            args.update(kwargs)
        subs = [TaskName._root_marker]
        subgroups = subgroups or []
        match [x for x in subtasks if x != None]:
            case [int() as i, TaskName() as x]:
                subs.append(str(i))
                subs.append(x.task.removeprefix(self.task + "."))
            case [str() as x]:
                subs.append(x)
            case [int() as x]:
                subs.append(str(x))
            case [*xs]:
                subs += xs

        return TaskName(head=self.head + subgroups,
                        tail=self.tail + subs,
                        meta=self.meta,
                        args=args,
                        )

    def job_head(self) -> TaskName:
        """ generate a canonical head/completion task name for this name
        eg: group::simple.task..$gen$.<UUID>
        ->  group::simple.task..$gen$.<UUID>..$head$

        """
        if TaskFlags.JOB_HEAD in self.meta:
            return self

        return self.subtask(TaskName._head_marker)

    def instantiate(self, *, prefix=None) -> TaskName:
        """ Generate a concrete instance of this name with a UUID appended,
        optionally can add a prefix
          # TODO possibly do $gen$.{prefix?}.<UUID>

          ie: a.task.group::task.name..{prefix?}.$gen$.<UUID>
        """
        uuid = uuid1()
        match prefix:
            case None:
                return self.subtask(TaskName._gen_marker, uuid, uuid=uuid)
            case _:
                return self.subtask(prefix, TaskName._gen_marker, uuid, uuid=uuid)

    def last(self) -> None|TailEntry:
        if bool(self.tail):
            return self.tail[-1]
        return None
