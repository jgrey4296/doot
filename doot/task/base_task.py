#!/usr/bin/env python3
"""
"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

printer = logmod.getLogger("doot._printer")

import doot
import doot.errors
import tomlguard
from doot._abstract import Task_i, Job_i, Action_p, PluginLoader_p
from doot.enums import TaskFlags, TaskStateEnum
from doot.structs import TaskStub, TaskStubPart, DootActionSpec, DootCodeReference, DootTaskName, DootTaskArtifact
from doot.actions.base_action import DootBaseAction
from doot.errors import DootTaskLoadError, DootTaskError

from doot.mixins.param_spec import ParamSpecMaker_m
from doot.mixins.importer import Importer_m

TASK_ALISES     = doot.aliases.task
PRINT_LOCATIONS = doot.constants.printer.PRINT_LOCATIONS
STATE_TASK_NAME_K : Final[str] = doot.constants.patterns.STATE_TASK_NAME_K

class _TaskProperties_m(ParamSpecMaker_m):

    @classmethod
    @property
    def param_specs(cls) -> list[DootParamSpec]:
        """  make class parameter specs  """
        return [
            cls.build_param(name="help", default=False, invisible=True, prefix="--"),
            cls.build_param(name="debug", default=False, invisible=True, prefix="--"),
            cls.build_param(name="verbose", default=0, type=int, invisible=True, prefix="--")
           ]

    @property
    def readable_name(self) -> str:
        return str(self.spec.name.readable)

    @property
    def actions(self):
        """lazy creation of action instances,
          `prepare_actions` has already ensured all ctors can be found
        """
        yield from iter(self.spec.actions)

    @property
    def name(self) -> str:
        return str(self.spec.name)

    @property
    def fullname(self) -> DootTaskName:
        return self.spec.name

    @property
    def short_doc(self) -> str:
        """ Generate Job Class 1 line help string """
        try:
            split_doc = [x for x in self.__class__.__doc__.split("\n") if bool(x)]
            return ":: " + split_doc[0].strip() if bool(split_doc) else ""
        except AttributeError:
            return ":: "

    @property
    def doc(self) -> list[str]:
        return self.spec.doc or self._help

    @property
    def depends_on(self) -> abc.Generator[str|DootTaskName]:
        for x in self.spec.depends_on:
            yield x

    @property
    def required_for(self) -> abc.Generator[str|DootTaskName]:
        for x in self.spec.required_for:
            yield x

    def add_execution_record(self, arg):
        """ Record some execution record information for display or debugging """
        self._records.append(arg)

    def log(self, msg, level=logmod.DEBUG, prefix=None) -> None:
        """
        utility method to log a message, useful as tasks are running
        """
        prefix : str       = prefix or ""
        lines  : list[str] = []
        match msg:
            case str():
                lines.append(msg)
            case types.LambdaType():
                lines.append(msg())
            case [types.LambdaType()]:
                lines += msg[0]()
            case list():
                lines += msg

        for line in lines:
            logging.log(level, prefix + str(line))

    @property
    def is_stale(self):
        return False

    def __hash__(self):
        return hash(self.name)

    def __lt__(self, other:Task_i) -> bool:
        """ Task A < Task B iff A ∈ B.run_after   """
        return (other.name in self.spec.after_artifacts
                or other.name in self.spec.depends_on)

    def __eq__(self, other):
        match other:
            case str():
                return self.name == other
            case Task_i():
                return self.name == other.name
            case _:
                return False

@doot.check_protocol
class DootTask(_TaskProperties_m, Importer_m, Task_i):
    """
      The simplest task, which can import action classes.
      eg:
      actions = [ {do = "doot.actions.shell_action:DootShellAction", args = ["echo", "this is a test"] } ]
    """
    action_ctor    = DootBaseAction
    _default_flags = TaskFlags.TASK
    _help          = ["The Simplest Task"]

    def __init__(self, spec, *, job=None, action_ctor=None, **kwargs):
        self.spec       : SpecStruct_p        = spec
        self.status     : TaskStateEnum       = TaskStateEnum.WAIT
        self.flags      : TaskFlags           = TaskFlags.JOB
        self._records   : list[Any]           = []
        self.state                            = dict(spec.extra)
        self.job                              = job
        self.state[STATE_TASK_NAME_K]         = self.spec.name
        self.state['_action_step']            = 0
        self.action_ctor                      = action_ctor
        self.prepare_actions()

    def __repr__(self):
        return f"<Task: {self.name}>"

    @classmethod
    def class_help(cls):
        """ Task *class* help. """
        help_lines = [f"Task   : {cls.__qualname__} v{cls._version}", ""]
        mro = " -> ".join(x.__name__ for x in cls.mro())
        help_lines.append(f"Task MRO: {mro}")
        help_lines.append("")
        help_lines += cls._help

        return "\n".join(help_lines)

    @classmethod
    def stub_class(cls, stub) -> TaskStub:
        """ Create a basic toml stub for this task"""
        if bool(list(filter(lambda x: x[0] == "task", TASK_ALISES))):
            stub.ctor = "task"
        else:
            stub.ctor                   = cls

        # Come first
        stub['active_when'].priority    = -90
        stub['required_for'].priority   = -90
        stub['depends_on'].priority     = -100

        stub['print_levels'].type       = f"Dict: {PRINT_LOCATIONS}"
        stub['print_levels'].default    = {"head":"INFO","build":"INFO","sleep":"INFO","action":"INFO", "execute":"INFO"}

        stub['priority'].default        = 10
        stub['queue_behaviour'].default = "default"
        stub['queue_behaviour'].comment = "default | auto | reactive"
        return stub

    def stub_instance(self, stub) -> TaskStub:
        """ extend the class toml stub with details from this instance """
        stub['name'].default      = self.fullname
        if bool(self.doc):
            stub['doc'].default   = self.doc[:]
        stub['flags'].default     = self.spec.flags

        return stub

    def prepare_actions(self):
        """ if the task/action spec requires particular action ctors, load them.
          if the action spec doesn't have a ctor, use the task's action_ctor
        """
        logging.info("Preparing Actions: %s", self.name)
        for group in self.spec.action_groups:
            for action_spec in group:
                match action_spec:
                    case DootTaskName() | DootTaskArtifact():
                        pass
                    case DootActionSpec() if action_spec.fun is not None:
                        pass
                    case DootActionSpec() if action_spec.do is not None:
                        action_ref = self.import_callable(action_spec.do)
                        action_spec.set_function(action_ref)
                    case DootActionSpec():
                        action_spec.set_function(self.action_ctor)
                    case _:
                        raise doot.errors.DootTaskError("Unknown element in action group: ", action_spec, self.spec.name)
