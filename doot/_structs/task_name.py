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

from pydantic import field_validator, ValidationError, model_validator
import importlib
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.enums import TaskFlags, ReportEnum
from doot._structs.structured_name import StructuredName, aware_splitter

class DootTaskName(StructuredName):
    """
      A Task Name.

    """

    meta               : TaskFlags               = TaskFlags.default
    args               : dict                    = {}
    version_constraint : None|str                = None

    _root              : None|DootTaskName       = None

    _separator          : ClassVar[str]           = doot.constants.patterns.TASK_SEP
    _gen_marker         : ClassVar[str]           = doot.constants.patterns.SPECIALIZED_ADD
    _internal_marker    : ClassVar[str]           = doot.constants.patterns.INTERNAL_TASK_PREFIX
    _head_marker        : ClassVar[str]           = doot.constants.patterns.SUBTASKED_HEAD

    @classmethod
    def build(cls, name:str|dict|DootTaskName, *, args=None):
        """ build a name from the various ways it can be specificed.
          handles a single string of the group and taskname,
          or a dict that specifies taskname and maybe the groupname

        """
        match name:
            case DootTaskName():
                return name
            case str() if cls._separator not in name:
                logging.debug("Taskname has no group, setting default")
                group = "default"
                task = name
            case str():
                group, task = name.split(doot.constants.patterns.TASK_SEP)
            case {"name": DootTaskName() as name}:
                return name
            case {"name": str() as name} if cls._separator not in name:
                logging.debug("Taskname has no group, setting default")
                group = "default"
                task  = name
            case {"name": str() as name}:
                group , task = name.split(doot.constants.patterns.TASK_SEP)
            case { "group": str() as group, "name": str() as task}:
                pass
            case _:
                raise doot.errors.DootError("Unrecognized name format: %s", name)

        return DootTaskName(head=[group], tail=[task], args=args or {})

    @field_validator("head", mode="before")
    def _process_head(cls, head):
        """ ensure the head is in its component parts """
        match head:
            case list():
                head = [x.replace('"',"").replace("'","") for x in head]
                head = ftz.reduce(lambda x, y: x + y, map(aware_splitter, head))
            case _:
                raise ValidationError("Bad Task Head Value", head)

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
                raise ValidationError("Bad Task Tail Value", tail)

        return tail

    @model_validator(mode="after")
    def check_metdata(self):
        if self.tail[0] == DootTaskName._internal_marker:
            self.meta |= TaskFlags.INTERNAL
        if DootTaskName._gen_marker in self.tail:
            self.meta |= TaskFlags.CONCRETE
        if DootTaskName._head_marker in self.tail:
            self.meta |= TaskFlags.JOB_HEAD

        if TaskFlags.CONCRETE in self.meta and 'uuid' not in self.args:
            raise ValidationError("Instanced Name lacks a stored uuid", self)
        if TaskFlags.CONCRETE in self.meta and DootTaskName._gen_marker not in self.tail:
            raise ValidationError("Specialized Name lacks the specialized keyword in its tail", self)
        if TaskFlags.INTERNAL in self.meta and not self.tail[0] == DootTaskName._internal_marker:
            raise ValidationError("Internal Name lacks a prefix underscore", self)

        return self

    def __str__(self) -> str:
        return "{}{}{}".format(self.group, self._separator, self.task)

    def __repr__(self) -> str:
        name = str(self)
        return f"<TaskName: {name}>"

    def __hash__(self):
        return hash(str(self))

    @property
    def group(self) -> str:
        fmt = "{}"
        if len(self.head) > 1:
            # fmt = "tasks.\"{}\""
            fmt = '"{}"'
        return fmt.format(self.head_str())

    @property
    def task(self) -> str:
        return self._subseparator.join([str(x) if not isinstance(x, UUID) else "${}$".format(hex(x.time_low)) for x in self.tail])

    @property
    def readable(self):
        group = self.group
        tail = self._subseparator.join([str(x) if not isinstance(x, UUID) else "<UUID>" for x in self.tail])
        return "{}{}{}".format(group, self._separator, tail)

    def is_instance(self) -> bool:
        return TaskFlags.CONCRETE in self.meta

    def match_version(self, other) -> bool:
        """ match version constraints of two task names against each other """
        raise NotImplementedError()

    def root(self) -> DootTaskName:
        """
        Strip off detail information to get the basic task name for id purposes
        """
        index = None
        if DootTaskName._gen_marker in self.tail:
            index = self.tail.index(DootTaskName._gen_marker)
        elif DootTaskName._head_marker in self.tail:
            index = self.tail.index(DootTaskName._head_marker)

        match index:
            case int():
                return DootTaskName(head=self.head[:], tail=self.tail[:index])
            case None:
                return self


    def subtask(self, *subtasks, subgroups:list[str]|None=None, **kwargs) -> DootTaskName:
        """ generate an extended name, with more information
        eg: a.group::simple.task
        ->  a.group::simple.task.targeting.something

        propagates args
        """

        args = self.args.copy() if self.args else {}
        if bool(kwargs):
            args.update(kwargs)
        subs = []
        subgroups = subgroups or []
        match [x for x in subtasks if x != None]:
            case [int() as i, DootTaskName() as x]:
                subs.append(str(i))
                subs.append(x.task.removeprefix(self.task + "."))
            case [str() as x]:
                subs.append(x)
            case [int() as x]:
                subs.append(str(x))
            case [*xs]:
                subs = xs

        return DootTaskName(head=self.head + subgroups,
                            tail=self.tail + subs,
                            meta=self.meta,
                            args=args,
                            _root=self.root())

    def job_head(self) -> DootTaskName:
        """ generate a canonical head/completion task name for this name
        eg: group::simple.task.$gen$.<UUID>
        ->  group::simple.task.$gen$.<UUID>.$head$

        """
        if TaskFlags.JOB_HEAD in self.meta:
            return self

        return self.subtask(DootTaskName._head_marker)

    def instantiate(self, *, prefix=None):
        """ Generate a concrete instance of this name with a UUID appended,
        optionally can add a prefix
          # TODO possibly do $gen$.{prefix?}.<UUID>

          ie: a.task.group::task.name.{prefix?}.$gen$.<UUID>
        """
        uuid = uuid1()
        match prefix:
            case None:
                return self.subtask(DootTaskName._gen_marker, uuid, uuid=uuid)
            case _:
                return self.subtask(prefix, DootTaskName._gen_marker, uuid, uuid=uuid)

    def last(self):
        return self.tail[-1]
