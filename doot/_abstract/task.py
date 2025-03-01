"""
Tasks are the main abstractions managed by Doot

  - JOBS create tasks
  - TASKS have actions
  - ACTIONS are individual atomic steps of a task, given the detailed information necessary to perform the step.

Jobs, as they can control refication order, can add setup and teardown tasks.
This can allow interleaving, or grouping.

  Communication paths:
  Job  -> Task   : by creation
  Task -> Action : by creation
  Action -> Task : by return value, updating task state dict
  Task -> Job    : by reference to the job

  Task -> Task     = Postboxes
  Action -> Action = Action -> Task State -> Action

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors

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

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from doot._abstract.protocols import ParamStruct_p, SpecStruct_p, StubStruct_p

    type ActionSpec = Any
    type TaskName   = str
    type ActionReturn = Maybe[dict|bool|ActionResponse_e]

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class TaskStatus_e(enum.Enum):
    """
      Enumeration of the different states a task/artifact can be in.
      The state is stored in the task object itself.

      Before a task object hsa been created, the tracker
      provides the status according to what specs exist for the task name.

    """
    # Pre-Task Object Creation statuses:
    NAMED           = enum.auto() # A Name, missing a spec
    DECLARED        = enum.auto() # Abstract Spec Exists

    DEFINED         = enum.auto() # Spec has been instantiated into the dependency network

    # Task Object Exists
    DISABLED        = enum.auto() # Artificial state for if a spec or task has been disabled.
    INIT            = enum.auto() # Task Object has been created.
    WAIT            = enum.auto() # Task is awaiting dependency check and pass
    READY           = enum.auto() # Dependencies are done, ready to execute/expand.
    RUNNING         = enum.auto() # Has been given to the runner, waiting for a status update.
    SKIPPED         = enum.auto() # Runner has signaled the task was skipped.
    HALTED          = enum.auto() # Task has reached minimum priority, timing out.
    FAILED          = enum.auto() # Runner has signaled Failure.
    SUCCESS         = enum.auto() # Runner has signaled success.
    TEARDOWN        = enum.auto() # Task is ready to be killed
    DEAD            = enum.auto() # Task is done.

    default         = NAMED

    @classmethod
    @property
    def pre_set(cls) -> set:
        return {cls.NAMED, cls.DECLARED, cls.DEFINED}

    @classmethod
    @property
    def success_set(cls) -> set:
        return {cls.SUCCESS, cls.TEARDOWN, cls.DEAD}

    @classmethod
    @property
    def fail_set(cls) -> set:
        return {cls.SKIPPED, cls.HALTED, cls.FAILED}

class ArtifactStatus_e(enum.Enum):
    """ States an artifact can be in """
    DECLARED = enum.auto() # doesn't exist or not checked
    STALE    = enum.auto() # Exists, but is old
    TOCLEAN  = enum.auto() # May exist, needs to be deleted
    EXISTS   = enum.auto() # Exists

class ActionResponse_e(enum.Enum):
    """
      Description of how a Action went.
    """

    SUCCEED    = enum.auto()
    FAIL       = enum.auto()
    SKIP       = enum.auto()
    SKIP_GROUP = enum.auto()
    SKIP_TASK  = enum.auto()

    # Aliases
    SUCCESS  = SUCCEED

##--|

@runtime_checkable
class Action_p(Protocol):
    """
    holds individual action information and state, and executes it
    """

    def __call__(self, spec:ActionSpec, task_state:dict) -> ActionReturn:
        pass
##--|

class Task_d:
    """ Core Interface for Tasks """

    _version         : str       = "0.1"
    _help            : list[str]
    doc              : list[str]

@runtime_checkable
class Task_p(Protocol):

    def __init__(self, spec:SpecStruct_p):
        pass

    def __hash__(self):
        pass

    def __lt__(self, other:TaskName|Task_d) -> bool:
        """ Task A < Task B iff A ∈ B.run_after   """
        pass

    def __eq__(self, other:Task_d) -> bool:
        pass

    def add_execution_record(self, arg:Any) -> None:
        """ Record some execution record information for display or debugging """
        pass

    def log(self, msg:str, level:int=logmod.DEBUG, prefix:Maybe[str]=None) -> None:
        """
          utility method to log a message, useful as tasks are running
        """
        pass

    def shortname(self) -> str:
        pass

    def name(self) -> TaskName:
        pass

@runtime_checkable
class Job_p(Task_p, Protocol):
    """
    builds tasks
    """

    def expand_job(self) -> list:
        pass
