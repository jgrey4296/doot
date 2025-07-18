#!/usr/bin/env python3
"""
A Utility implementation of most of what a task needs
"""
# mypy: disable-error-code="attr-defined"
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Mixin, Proto
from jgdv.cli import ParamSpecMaker_m
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.errors import StructLoadError, TaskError

# ##-- end 1st party imports

# ##-| Local
from ._interface import (Action_p, Job_p, QueueMeta_e, Task_p, RelationSpec_i,
                         TaskMeta_e, TaskStatus_e, TaskSpec_i, TaskName_p, ActionSpec_i)
from .structs import RelationSpec, TaskArtifact, ActionSpec, TaskName

# # End of Imports.

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload
from types import LambdaType

if TYPE_CHECKING:
    from jgdv import Maybe, Lambda
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from jgdv._abstract.protocols import SpecStruct_p
    from jgdv.cli import ParamSpec
    from doot.cmds.structs.task_stub import TaskStub
    from . import TaskSpec

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

TASK_ALISES                    = doot.aliases.task
PRINT_LOCATIONS                = doot.constants.printer.PRINT_LOCATIONS
STATE_TASK_NAME_K : Final[str] = doot.constants.patterns.STATE_TASK_NAME_K

class _TaskActionPrep_m:

    def prepare_actions(self) -> None:
        """ if the task/action spec requires particular action ctors, load them.
          if the action spec doesn't have a ctor, use the task's action_ctor

        collects any action errors together, then raises them as a task error
        """
        logging.debug("Preparing Actions: %s", self.name)
        failed : list[Exception] = []
        for action_spec in self.spec.action_group_elements():
            match action_spec:
                case RelationSpec():
                    pass
                case ActionSpec() if action_spec.fun is not None:
                    pass
                case ActionSpec() if action_spec.do is not None:
                    try:
                        action_spec.set_function()
                    except (doot.errors.StructError, ImportError) as err:
                        failed.append(err)
                case ActionSpec():
                    action_spec.set_function(fun=self.action_ctor)
                case _:
                    failed.append(doot.errors.TaskError("Unknown element in action group: ", action_spec, self.name))
        else:
            match failed:
                case []:
                    pass
                case [*xs]:
                    raise doot.errors.TaskError("Action Spec preparation failures", self.name[:], xs)

class _TaskProperties_m:

    @classmethod
    def param_specs(cls) -> list[ParamSpec]:
        """  make class parameter specs  """
        return [
            cls.build_param(name="--help",    default=False,       implicit=True),
            cls.build_param(name="--debug",   default=False,       implicit=True),
            cls.build_param(name="--verbose", default=0, type=int, implicit=True),
           ]

    @property
    def name(self) -> TaskName:
        return self.spec.name

    @property
    def short_doc(self) -> str:
        """ Generate Job Class 1 line help string """
        if self.__class__.__doc__ is None:
            return ":: "
        try:
            split_doc = [x for x in self.__class__.__doc__.split("\n") if bool(x)]
            return ":: " + split_doc[0].strip() if bool(split_doc) else ""
        except AttributeError:
            return ":: "

    @property
    def doc(self) -> list[str]:
        return self.spec.doc or self._help

    @property
    def is_stale(self) -> bool:
        return False

class _TaskStubbing_m:

    @classmethod
    def stub_class(cls, stub:TaskStub) -> TaskStub:
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
        stub['flags'].comment = " | ".join({x.name for x in TaskMeta_e})
        return stub

    def stub_instance(self, stub:TaskStub) -> TaskStub:
        """ extend the class toml stub with details from this instance """
        stub['name'].default      = self.name.de_uniq()
        if bool(self.doc):
            stub['doc'].default   = self.doc[:]
        else:
            stub['doc'].default   = []
        stub['flags'].default     = self.spec.flags

        return stub

class _TaskHelp_m:

    @classmethod
    def class_help(cls) -> list[str]:
        """ Task *class* help. """
        help_lines = [f"Task   : {cls.__qualname__} v{cls._version}", ""]
        mro = " -> ".join(x.__name__ for x in cls.mro())
        help_lines.append(f"Task MRO: {mro}")
        help_lines.append("")
        help_lines += cls._help

        return help_lines

##--|

@Proto(Task_p, check=True)
@Mixin(ParamSpecMaker_m, _TaskProperties_m, _TaskStubbing_m, _TaskHelp_m, _TaskActionPrep_m)
class DootTask:
    """
      The simplest task, which can import action classes.
      eg:
      actions = [ {do = "doot.workflow.actions.shell_action:DootShellAction", args = ["echo", "this is a test"] } ]

      Actions are imported upon task creation.
    """
    Flags            : ClassVar[type[TaskMeta_e]]   = TaskMeta_e
    INITIAL_STATE    : ClassVar[TaskStatus_e]       = TaskStatus_e.INIT
    COMPLETE_STATES  : ClassVar[set[TaskStatus_e]]  = {TaskStatus_e.SUCCESS}
    _default_flags   : ClassVar                     = {TaskMeta_e.TASK}
    action_ctor      : type
    _help            : tuple[str, ...]  = tuple(["The Simplest Task"])
    _version         : str              = "0.1"
    _internal_state  : dict

    def __init__(self, spec:TaskSpec_i, *, action_ctor:Maybe[Callable]=None, **kwargs:Any):  # noqa: ARG002
        self.flags                               = TaskMeta_e.TASK
        self._internal_state                     = dict(spec.extra)
        self._spec                               = spec
        self._priority                           = self.spec.priority
        self._status                             = DootTask.INITIAL_STATE

        self._internal_state[STATE_TASK_NAME_K]  = self.spec.name
        self._internal_state['_action_step']     = 0

        match action_ctor:
            case None:
                from .actions import DootBaseAction  # noqa: PLC0415
                self.action_ctor = DootBaseAction
            case type() as x:
                self.action_ctor  = x
            case x:
                raise TypeError(type(x))


    ##--| dunders

    @override
    def __repr__(self) -> str:
        cls = self.__class__.__qualname__
        return f"<{cls}: {self.name.de_uniq()}>"

    def __bool__(self) -> bool:
        return self.status in DootTask.COMPLETE_STATES

    @override
    def __hash__(self) -> int:
        return hash(self.name)

    def __lt__(self, other:TaskName_p|Task_p) -> bool:
        """ Task A < Task B if B ∈ A.depends_on """
        match other:
            case TaskName_p():
                name = other.name
            case Task_p():
                name = other.spec.name
            case x:
                raise TypeError(type(x))
        return any(name in x.target for x in self.spec.depends_on if isinstance(x, RelationSpec_i))

    @override
    def __eq__(self, other:object) -> bool:
        match other:
            case str() | TaskName():
                return self.name == other
            case Task_p():
                return self.name == other.name
            case _:
                return False

    ##--| properties

    @property
    def name(self) -> TaskName_p:
        return self.spec.name

    @property
    def spec(self) -> TaskSpec_i:
        return self._spec

    @property
    def status(self) -> TaskStatus_e:
        return self._status


    @status.setter
    def status(self, val:TaskStatus_e) -> None:
        self._status = val

    @property
    def priority(self) -> int:
        return self._priority

    @priority.setter
    def priority(self, val:int) -> None:
        self._priority = val

    @property
    def internal_state(self) -> dict:
        return self._internal_state
    ##--| methods

    def prepare_actions(self) -> None:
        """ if the task/action spec requires particular action ctors, load them.
          if the action spec doesn't have a ctor, use the task's action_ctor

        collects any action errors together, then raises them as a task error
        """
        logging.debug("Preparing Actions: %s", self.name)
        failed : list[Exception] = []
        for action_spec in self.spec.action_group_elements():
            match action_spec:
                case RelationSpec_i():
                    pass
                case ActionSpec_i() if action_spec.fun is not None:
                    pass
                case ActionSpec_i() if action_spec.do is not None:
                    try:
                        action_spec.set_function()
                    except (doot.errors.StructError, ImportError) as err:
                        failed.append(err)
                case ActionSpec_i():
                    action_spec.set_function(fun=self.action_ctor)
                case _:
                    failed.append(doot.errors.TaskError("Unknown element in action group: ", action_spec, self.name))
        else:
            match failed:
                case []:
                    pass
                case [*xs]:
                    raise doot.errors.TaskError("Action Spec preparation failures", self.name[:], xs)

    def log(self, msg:str|Lambda|list, level:int=logmod.DEBUG, prefix:Maybe[str]=None) -> None:
        """
        utility method to log a message, useful as tasks are running
        """
        prefix = prefix or ""
        assert(prefix is not None)
        lines  : list[str] = []
        match msg:
            case str():
                lines.append(msg)
            case LambdaType():
                lines.append(msg())
            case [LambdaType()]:
                lines += msg[0]()
            case list():
                lines += msg

        for line in lines:
            logging.log(level, prefix + str(line))

    def get_action_group(self, group_name:str) -> list[ActionSpec_i]:
        if not bool(group_name):
            raise TaskError("Tried to retrieve an empty groupname")
        if hasattr(self, group_name):
            return getattr(self, group_name)
        if hasattr(self.spec, group_name):
            return getattr(self.spec, group_name)

        logging.warning("Unknown Groupname: %s", group_name)
        return []
