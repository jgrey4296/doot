"""TASKS ARE THE MAIN ABSTRACTIONS MANAGED BY DOOT

  - JOBS create tasks
  - TASKS have actions
  - ACTIONS are individual atomic steps of a task, given the detailed information necessary to perform the step.

Jobs, as they can control refication order, can add setup and teardown tasks.
This can allow interleaving, or grouping.

  Communication:
  Job  -> Task   : by creation
  Task -> Action : by creation
  Action -> Task : by return value, updating task state dict
  Task -> Job    : by reference to the job

  Task -> Task     = Task -> Job -> Task
  Action -> Action = Action -> Task -> Action

"""
from __future__ import annotations

import logging as logmod
import abc
import types
from typing import Generator, NewType, Protocol, Any, runtime_checkable

from tomlguard import TomlGuard

import doot
import doot.errors
from doot.enums import TaskFlags, TaskStateEnum, ActionResponseEnum
from doot._abstract.structs import StubStruct_p, SpecStruct_p, ParamStruct_p
from doot._structs.task_name import DootTaskName
from doot._structs.action_spec import DootActionSpec

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


@runtime_checkable
class Action_p(Protocol):
    """
    holds individual action information and state, and executes it
    """
    _toml_kwargs : ClassVar[list[str]] = []

    @abc.abstractmethod
    def __call__(self, spec:DootActionSpec, task_state:dict) -> dict|bool|ActionResponseEnum|None:
        raise NotImplementedError()

class _TaskBase_i:
    """ Core Interface for Tasks """

    _version         : str       = "0.1"
    _help            : list[str] = []

    @classmethod
    @property
    @abc.abstractmethod
    def param_specs(cls) -> list[ParamStruct_p]:
        """  make class parameter specs  """
        pass

    @abc.abstractmethod
    def __init__(self, spec:SpecStruct_p):
        pass

    @property
    @abc.abstractmethod
    def readable_name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def fullname(self) -> DootTaskName:
        pass

    @abc.abstractmethod
    def __hash__(self):
        pass

    @abc.abstractmethod
    def __lt__(self, other:_TaskBase_i) -> bool:
        """ Task A < Task B iff A ∈ B.run_after   """
        pass

    @abc.abstractmethod
    def __eq__(self, other):
        pass

    @property
    @abc.abstractmethod
    def short_doc(self) -> str:
        """ Generate Job Class 1 line help string """
        pass

    @property
    @abc.abstractmethod
    def doc(self) -> list[str]:
        pass

    @property
    @abc.abstractmethod
    def depends_on(self) -> abc.Generator[str|DootTaskName]:
        pass

    @property
    @abc.abstractmethod
    def required_for(self) -> abc.Generator[str|DootTaskName]:
        pass

    @abc.abstractmethod
    def add_execution_record(self, arg):
        """ Record some execution record information for display or debugging """
        pass

    @abc.abstractmethod
    def log(self, msg, level=logmod.DEBUG, prefix=None) -> None:
        """
          utility method to log a message, useful as tasks are running
        """
        pass

    @classmethod
    @abc.abstractmethod
    def class_help(cls) -> str:
        pass

    @classmethod
    @abc.abstractmethod
    def stub_class(cls, stub:StubStruct_p):
        """
        Specialize a StubStruct_p to describe this class
        """
        pass

    @abc.abstractmethod
    def stub_instance(self, stub:StubStruct_p):
        """
          Specialize a StubStruct_p with the settings of this specific instance
        """
        pass

    @property
    @abc.abstractmethod
    def is_stale(self) -> bool:
        """ Query whether the task's artifacts have become stale and need to be rebuilt"""
        pass

class Task_i(_TaskBase_i):
    """
    holds task information and state, produces actions to execute.

    """

    @classmethod
    @abc.abstractmethod
    def class_help(cls):
        """ Task *class* help. """
        pass

    @property
    @abc.abstractmethod
    def actions(self) -> Generator[Action_p]:
        """lazy creation of action instances"""
        pass

class Job_i(Task_i):
    """
    builds tasks
    """

    @classmethod
    @abc.abstractmethod
    def class_help(cls) -> str:
        """ Job *class* help. """
        pass

    @abc.abstractmethod
    def default_task(self, name:str|DootTaskName|None, extra:None|dict|TomlGuard) -> SpecStruct_p:
        raise NotImplementedError(self.__class__, "default_task")

    @abc.abstractmethod
    def specialize_task(self, task:SpecStruct_p) -> SpecStruct_p|None:
        raise NotImplementedError(self.__class__, "specialize_task")
