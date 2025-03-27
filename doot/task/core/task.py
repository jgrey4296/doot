#!/usr/bin/env python3
"""
A Utility implementation of most of what a task needs
"""
# ruff: noqa: C409
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
from jgdv import Proto, Mixin
from jgdv.structs.strang import CodeReference
from jgdv.cli.param_spec.builder_mixin import ParamSpecMaker_m
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.actions.core.action import DootBaseAction
from doot.enums import TaskMeta_e, QueueMeta_e, TaskStatus_e
from doot.errors import TaskError, StructLoadError
from doot._structs.action_spec import ActionSpec
from doot._structs.artifact import TaskArtifact
from doot._structs.task_name import TaskName
from doot._structs.relation_spec import RelationSpec
from doot._abstract import Task_d

# ##-- end 1st party imports

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

from doot._abstract import Action_p, Job_p, PluginLoader_p, Task_p

if TYPE_CHECKING:
    from jgdv import Maybe, Lambda
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from doot.structs import ParamSpec, TaskStub
    from doot._abstract import SpecStruct_p

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

TASK_ALISES                    = doot.aliases.task
PRINT_LOCATIONS                = doot.constants.printer.PRINT_LOCATIONS
STATE_TASK_NAME_K : Final[str] = doot.constants.patterns.STATE_TASK_NAME_K

class _TaskProperties_m:

    @classmethod
    @property
    def param_specs(cls) -> list[ParamSpec]:
        """  make class parameter specs  """
        return [
            cls.build_param(name="--help",    default=False,       implicit=True),
            cls.build_param(name="--debug",   default=False,       implicit=True),
            cls.build_param(name="--verbose", default=0, type=int, implicit=True),
           ]

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
    def is_stale(self) -> bool:
        return False

class _TaskStubbing_m:

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
        stub['flags'].comment = " | ".join({x.name for x in TaskMeta_e})
        return stub

    def stub_instance(self, stub) -> TaskStub:
        """ extend the class toml stub with details from this instance """
        stub['name'].default      = self.shortname
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
@Proto(Task_p, check=False)
@Mixin(ParamSpecMaker_m, _TaskProperties_m, _TaskStubbing_m, _TaskHelp_m)
class DootTask(Task_d):
    """
      The simplest task, which can import action classes.
      eg:
      actions = [ {do = "doot.actions.shell_action:DootShellAction", args = ["echo", "this is a test"] } ]

      Actions are imported upon task creation.
    """
    action_ctor                                   = DootBaseAction
    _default_flags                                = TaskMeta_e.TASK
    _help            : ClassVar[tuple[str]]       = tuple(["The Simplest Task"])
    COMPLETE_STATES  : Final[set[TaskStatus_e]]   = {TaskStatus_e.SUCCESS}
    INITIAL_STATE    : Final[TaskStatus_e]        = TaskStatus_e.INIT

    def __init__(self, spec, *, job=None, action_ctor=None, **kwargs):
        self.spec        : SpecStruct_p        = spec
        self.priority    : int                 = self.spec.priority
        self.status      : TaskStatus_e        = DootTask.INITIAL_STATE
        self.flags       : TaskMeta_e           = TaskMeta_e.TASK
        self.state       : dict                = dict(spec.extra)
        self.action_ctor : callable            = action_ctor
        self._records    : list[Any]           = []

        self.state[STATE_TASK_NAME_K]          = self.spec.name
        self.state['_action_step']             = 0

        self.prepare_actions()

    def __repr__(self):
        cls = self.__class__.__qualname__
        return f"<{cls}: {self.shortname}>"

    def __bool__(self):
        return self.status in DootTask.COMPLETE_STATES

    def __hash__(self):
        return hash(self.name)

    def __lt__(self, other:TaskName|Task_p) -> bool:
        """ Task A < Task B if A ∈ B.run_after or B ∈ A.runs_before  """
        return any(other.name in x.target for x in self.spec.depends_on)

    def __eq__(self, other:str|TaskName|Task_p):
        match other:
            case str() | TaskName():
                return self.name == other
            case Task_p():
                return self.name == other.name
            case _:
                return False

    def prepare_actions(self) -> None:
        """ if the task/action spec requires particular action ctors, load them.
          if the action spec doesn't have a ctor, use the task's action_ctor

        collects any action errors together, then raises them as a task error
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
                        action_spec.set_function()
                    except (doot.errors.StructError, ImportError) as err:
                        failed.append(err)
                case ActionSpec():
                    action_spec.set_function(fun=self.action_ctor)
                case _:
                    failed.append(doot.errors.TaskError("Unknown element in action group: ", action_spec, self.shortname))
        else:
            match failed:
                case []:
                    pass
                case [*xs]:
                    raise doot.errors.TaskError("Action Spec preparation failures", xs)

    def add_execution_record(self, arg) -> None:
        """ Record some execution record information for display or debugging """
        self._records.append(arg)

    def log(self, msg:str|Lambda|list, level=logmod.DEBUG, prefix=None) -> None:
        """
        utility method to log a message, useful as tasks are running
        """
        prefix : str       = prefix or ""
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

    def get_action_group(self, group_name:str) -> list:
        if not bool(group_name):
            raise TaskError("Tried to retrieve an empty groupname")
        if hasattr(self, group_name):
            return getattr(self, group_name)
        if group_name in self.spec.model_fields or self.spec.model_extra:
            return getattr(self.spec, group_name)

        logging.warning("Unknown Groupname: %s", group_name)
        return []
