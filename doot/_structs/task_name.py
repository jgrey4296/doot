#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
# import abc
import datetime
import enum
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Self, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import more_itertools as mitz
from pydantic import field_validator, model_validator
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._structs.structured_name import (StructuredName, TailEntry,
                                           aware_splitter)
from doot.enums import Report_f, TaskMeta_f

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class _TaskNameOps_m:
    """ Operations Mixin for manipulating TaskNames """

    def is_instance(self) -> bool:
        """ utility method to test if this name refers to a concrete task """
        return TaskMeta_f.CONCRETE in self.meta

    def match_version(self, other) -> bool:
        """ match version constraints of two task names against each other """
        raise NotImplementedError()

    def has_root(self) -> bool:
        """ Test for if the name has a a root marker, not at the end of the name"""
        match self._roots:
            case [-1, -1]:
                return False
            case _:
                return True

    def root(self, *, top=False) -> TaskName:
        """
        Strip off one root marker's worth of the name, or to the top marker.
        eg:
        root(test::a.b.c..<UUID>.sub..other) => test::a.b.c..<UUID>.sub.
        root(test::a.b.c..<UUID>.sub..other, top=True) => test::a.b.c.

        """
        match self._roots:
            case [-1, -1]:
                return self
            case [x, _] if top:
                return TaskName(head=self.head[:], tail=self.tail[:x])
            case [_, x]:
                return TaskName(head=self.head[:], tail=self.tail[:x])

    def add_root(self) -> TaskName:
        """ Add a root marker if the last element isn't already a root marker
        eg: group::a.b.c => group.a.b.c.
        (note the trailing '.')
        """
        match self.last():
            case x if x == TaskName._root_marker:
                return self
            case _:
                return self.subtask()

    def subtask(self, *subtasks, subgroups:list[str]|None=None, **kwargs) -> TaskName:
        """ generate an extended name, with more information
        eg: a.group::simple.task
        ->  a.group::simple.task..targeting.something

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
        eg: (concrete) group::simple.task..$gen$.<UUID> ->  group::simple.task..$gen$.<UUID>..$head$
        eg: (abstract) group::simple.task. -> group::simple.task..$head$

        """
        if TaskMeta_f.JOB_HEAD in self.meta:
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
        """
        Get the last value of the task/tail
        """
        if bool(self.tail):
            return self.tail[-1]
        return None

class TaskName(StructuredName, _TaskNameOps_m):
    """
      A Task Name.
      Infers metadata(TaskMeta_f) from the string data it is made of.
      a trailing '+' in the head makes it a job
      a leading '_' in the tail makes it an internal name, eg: group::_.task
      having a '$gen$' makes it a concrete name
      having a '$head$' makes it a job head
      Two separators in a row marks a recall point for root()

      TODO: parameters
    """

    meta                : TaskMeta_f               = TaskMeta_f.default
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
            self.meta |= TaskMeta_f.JOB
        if self.tail[0] == TaskName._internal_marker:
            self.meta |= TaskMeta_f.INTERNAL
        if TaskName._gen_marker in self.tail:
            self.meta |= TaskMeta_f.CONCRETE
        if TaskName._head_marker in self.tail:
            self.meta |= TaskMeta_f.JOB_HEAD
            self.meta &= ~TaskMeta_f.JOB

        if TaskMeta_f.CONCRETE in self.meta and 'uuid' not in self.args:
            raise ValueError("Instanced Name lacks a stored uuid", self)
        if TaskMeta_f.CONCRETE in self.meta and TaskName._gen_marker not in self.tail:
            raise ValueError("Specialized Name lacks the specialized keyword in its tail", self)
        if TaskMeta_f.INTERNAL in self.meta and not self.tail[0] == TaskName._internal_marker:
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
        """
        Test if self contains a certain meta flag, or if self conceptually includes other
        """
        match other:
            case TaskMeta_f():
                return other in self.meta
            case _:
                return super().__contains__(other)

    @ftz.cached_property
    def group(self) -> str:
        """ Format the group string of the task name """
        fmt = "{}"
        if len(self.head) > 1:
            # fmt = "tasks.\"{}\""
            fmt = '"{}"'
        return fmt.format(self.head_str())

    @ftz.cached_property
    def task(self) -> str:
        """
        Format with a minimal about of UUID information to tell different tasks apart
        """
        return self._subseparator.join([str(x) if not isinstance(x, UUID) else "${}$".format(hex(x.time_low)) for x in self.tail])

    @ftz.cached_property
    def readable(self):
        """ format this name to a readable form
        ie: elide uuids as just <UUID>
        """
        group = self.group
        tail = self._subseparator.join([str(x) if not isinstance(x, UUID) else "<UUID>" for x in self.tail])
        return "{}{}{}".format(group, self._separator, tail)
