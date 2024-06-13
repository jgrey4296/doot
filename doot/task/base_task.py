#!/usr/bin/env python3
"""
"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
import tomlguard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import Action_p, Job_i, PluginLoader_p, Task_i
from doot.actions.base_action import DootBaseAction
from doot.enums import TaskMeta_f, QueueMeta_e, TaskStatus_e
from doot.errors import DootTaskError, DootTaskLoadError
from doot.mixins.param_spec import ParamSpecMaker_m
from doot.structs import (ActionSpec, CodeReference, TaskArtifact,
                          TaskName)
from doot._structs.relation_spec import RelationSpec

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

TASK_ALISES                    = doot.aliases.task
PRINT_LOCATIONS                = doot.constants.printer.PRINT_LOCATIONS
STATE_TASK_NAME_K : Final[str] = doot.constants.patterns.STATE_TASK_NAME_K

class _TaskProperties_m(ParamSpecMaker_m):

    @classmethod
    @property
    def param_specs(cls) -> list[ParamSpec]:
        """  make class parameter specs  """
        return [
            cls.build_param(name="help", default=False, invisible=True, prefix="--"),
            cls.build_param(name="debug", default=False, invisible=True, prefix="--"),
            cls.build_param(name="verbose", default=0, type=int, invisible=True, prefix="--")
           ]

    @property
    def actions(self):
        """lazy creation of action instances,
          `prepare_actions` has already ensured all ctors can be found
        """
        yield from iter(self.spec.actions)

    @property
    def shortname(self) -> str:
        return str(self.spec.name.readable)

    @property
    def name(self) -> TaskName:
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
    def is_stale(self):
        return False

@doot.check_protocol
class DootTask(_TaskProperties_m, Task_i):
    """
      The simplest task, which can import action classes.
      eg:
      actions = [ {do = "doot.actions.shell_action:DootShellAction", args = ["echo", "this is a test"] } ]

      Actions are imported upon task creation.
    """
    action_ctor                                   = DootBaseAction
    _default_flags                                = TaskMeta_f.TASK
    _help                                         = ["The Simplest Task"]
    COMPLETE_STATES  : Final[set[TaskStatus_e]]   = {TaskStatus_e.SUCCESS, TaskStatus_e.EXISTS}
    INITIAL_STATE    : Final[TaskStatus_e]        = TaskStatus_e.INIT

    def __init__(self, spec, *, job=None, action_ctor=None, **kwargs):
        self.spec        : SpecStruct_p        = spec
        self.priority    : int                 = self.spec.priority
        self.status      : TaskStatus_e        = DootTask.INITIAL_STATE
        self.flags       : TaskMeta_f           = TaskMeta_f.TASK
        self.state       : dict                = dict(spec.extra)
        self.action_ctor : callable            = action_ctor
        self._records    : list[Any]           = []

        self.state[STATE_TASK_NAME_K]          = self.spec.name
        self.state['_action_step']             = 0

        self.prepare_actions()

    def __repr__(self):
        return f"<Task: {self.shortname}>"

    def __bool__(self):
        return self.status in DootTask.COMPLETE_STATES

    def __hash__(self):
        return hash(self.name)

    def __lt__(self, other:TaskName|Task_i) -> bool:
        """ Task A < Task B if A ∈ B.run_after or B ∈ A.runs_before  """
        return any(other.name in x.target for x in self.spec.depends_on)

    def __eq__(self, other):
        match other:
            case str() | TaskName():
                return self.name == other
            case Task_i():
                return self.name == other.name
            case _:
                return False

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
        stub['required_for'].priority   = -90
        stub['depends_on'].priority     = -100

        stub['priority'].default        = 10
        stub['queue_behaviour'].default = "default"
        stub['queue_behaviour'].comment = " | ".join({x.name for x in QueueMeta_e})
        stub['flags'].comment = " | ".join({x.name for x in TaskMeta_f})
        return stub

    def stub_instance(self, stub) -> TaskStub:
        """ extend the class toml stub with details from this instance """
        stub['name'].default      = self.shortname
        if bool(self.doc):
            stub['doc'].default   = self.doc[:]
        stub['flags'].default     = self.spec.flags

        return stub

    def prepare_actions(self):
        """ if the task/action spec requires particular action ctors, load them.
          if the action spec doesn't have a ctor, use the task's action_ctor
        """
        logging.debug("Preparing Actions: %s", self.shortname)
        failed = []
        for action_spec in self.spec.action_group_elements():
            match action_spec:
                case RelationSpec():
                    pass
                case ActionSpec() if action_spec.fun is not None:
                    pass
                case ActionSpec() if action_spec.do is not None:
                    try:
                        action_ctor = action_spec.do.try_import()
                        action_spec.set_function(action_ctor)
                    except ImportError as err:
                        failed.append(err)
                case ActionSpec():
                    action_spec.set_function(self.action_ctor)
                case _:
                    failed.append(doot.errors.DootTaskError("Unknown element in action group: ", action_spec, self.shortname))

        match failed:
            case []:
                pass
            case [x]:
                raise x
            case [*xs]:
                raise ImportError("Multiple Action Spec import failures", xs)

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
