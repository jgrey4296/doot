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
from doot.enums import TaskMeta_f, TaskStatus_e, ActionResponse_e
from doot._abstract.protocols import StubStruct_p, SpecStruct_p, ParamStruct_p

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@runtime_checkable
class Action_p(Protocol):
    """
    holds individual action information and state, and executes it
    """
    _toml_kwargs : ClassVar[list[str]] = []

    def __call__(self, spec:"ActionSpec", task_state:dict) -> dict|bool|ActionResponse_e|None:
        raise NotImplementedError()

class Task_i:
    """ Core Interface for Tasks """

    _version         : str       = "0.1"
    _help            : list[str] = []

    @abc.abstractmethod
    def __init__(self, spec:SpecStruct_p):
        pass

    @property
    @abc.abstractmethod
    def shortname(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def name(self) -> "TaskName":
        pass

    @abc.abstractmethod
    def __hash__(self):
        pass

    @abc.abstractmethod
    def __lt__(self, other:"TaskName"|Task_i) -> bool:
        """ Task A < Task B iff A ∈ B.run_after   """
        pass

    @abc.abstractmethod
    def __eq__(self, other):
        pass

    @property
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

class Job_i(Task_i):
    """
    builds tasks
    """
    pass
