#!/usr/bin/env python3
"""

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
from pydantic import field_validator, model_validator
from jgdv.structs.strang import Strang
from jgdv.enums.util import FlagsBuilder_m

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

CLEANUP_MARKER : Final[str] = "$cleanup$"

aware_splitter = str

class TaskMeta_f(FlagsBuilder_m, enum.Flag):
    """
      Flags describing properties of a task,
      stored in the Task_i instance itself.
    """

    TASK         = enum.auto()
    JOB          = enum.auto()
    TRANSFORMER  = enum.auto()

    INTERNAL     = enum.auto()
    JOB_HEAD     = enum.auto()
    CONCRETE     = enum.auto()
    DISABLED     = enum.auto()

    EPHEMERAL    = enum.auto()
    IDEMPOTENT   = enum.auto()
    REQ_TEARDOWN = enum.auto()
    REQ_SETUP    = enum.auto()
    IS_TEARDOWN  = enum.auto()
    IS_SETUP     = enum.auto()
    THREAD_SAFE  = enum.auto()
    STATEFUL     = enum.auto()
    STATELESS    = enum.auto()
    VERSIONED    = enum.auto()

    default      = TASK

class _TaskNameOps_m:
    """ Operations Mixin for manipulating TaskNames """

    def job_head(self) -> TaskName:
        """ generate a canonical head/completion task name for this name
        eg: (concrete) group::simple.task..$gen$.<UUID> ->  group::simple.task..$gen$.<UUID>..$head$
        eg: (abstract) group::simple.task. -> group::simple.task..$head$

        """
        stripped = self.uninstantiate()
        if TaskMeta_f.JOB_HEAD in stripped:
            return stripped

        return stripped.subtask(TaskName._head_marker)

    def cleanup_name(self) -> TaskName:
        """ canonical cleanup name """
        stripped = self.uninstantiate()
        if  stripped.last() == CLEANUP_MARKER:
            return stripped

        return stripped.subtask(CLEANUP_MARKER)

    def is_instantiated(self) -> bool:
        """ utility method to test if this name refers to a concrete task """
        return TaskMeta_f.CONCRETE in self.meta and isinstance(self.last(), UUID)

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

    def instantiate(self, *, prefix=None) -> TaskName:
        """ Generate a concrete instance of this name with a UUID appended,
        optionally can add a prefix
          # TODO possibly do $gen$.{prefix?}.<UUID>

          ie: a.task.group::task.name..{prefix?}.$gen$.<UUID>
        """
        if isinstance(self.last(), UUID):
            return self

        stripped = self.uninstantiate()

        uuid = uuid1()
        match prefix:
            case None:
                return stripped.subtask(TaskName._gen_marker, uuid)
            case _:
                return stripped.subtask(prefix, TaskName._gen_marker, uuid)

    def uninstantiate(self) -> TaskName:
        """ take a name and remove the $gen$.{prefix?}.<UUID> parts """
        if not bool(self.args.get('uuids', None)):
            return self

        meta = self.meta & (~ TaskMeta_f.CONCRETE)
        args = self.args.copy()
        del args['uuids']

        def filter_tail(x,y) -> bool:
            if (gen_marker:=y == TaskName._gen_marker) and x == "" :
                return False
            if gen_marker or isinstance(x, UUID):
                return False
            if isinstance(y, UUID):
                return False
            return True

        cleaned_tail = [x for x,y in zip(self.tail, self.tail[1:]) if filter_tail(x,y)]
        if not isinstance(self.tail[-1], UUID):
            cleaned_tail.append(self.tail[-1])

        return TaskName(head=self.head,
                        tail=cleaned_tail,
                        meta=meta,
                        args=args
                        )

    def last(self):
        """
        Get the last value of the task/tail
        """
        if bool(self.tail):
            return self.tail[-1]
        return None

class TaskName(Strang, _TaskNameOps_m):
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

    def __lt__(self, other):
        match other:
            case TaskName() if self == other:
                return False
            case TaskName():
                stripped = self.uninstantiate()
                return super(TaskName, stripped).__lt__(other.uninstantiate().instantiate())
            case _:
                return super().__lt__(self, other)

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
