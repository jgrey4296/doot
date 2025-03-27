#!/usr/bin/env python3
"""

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
import re
import time
import types
from abc import abstractmethod
from collections import defaultdict, deque
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.mixins.enum_builders import EnumBuilder_m, FlagsBuilder_m

# ##-- end 3rd party imports

# ##-- 1st party imports

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
    from jgdv import Maybe, Ident, Depth
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from doot._abstract.protocols import ArtifactStruct_p, SpecStruct_p
    from doot._abstract.task import Task_p
    type Actual      = Any
    type TaskSpec    = Any
    type TaskStatus_e = enum.Enum
    type Abstract[T] = T
    type Concrete[T] = T
    type PlanEntry   = tuple[Depth, Concrete[Ident], str]

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class EdgeType_e(EnumBuilder_m, enum.Enum):
    """ Enum describing the possible edges of the task tracker's task network """

    TASK              = enum.auto() # task to task
    ARTIFACT_UP       = enum.auto() # abstract to concrete artifact
    ARTIFACT_DOWN     = enum.auto() # concrete to abstract artifact
    TASK_CROSS        = enum.auto() # Task to artifact
    ARTIFACT_CROSS    = enum.auto() # artifact to task

    default           = TASK

    @classmethod
    @property
    def artifact_edge_set(cls) -> set[enum.Enum]:
        return  {cls.ARTIFACT_UP, cls.ARTIFACT_DOWN, cls.TASK_CROSS}

class QueueMeta_e(EnumBuilder_m, enum.Enum):
    """ available ways a task can be activated for running
      onRegister/auto     : activates automatically when added to the task network
      reactive            : activates if an adjacent node completes

      default             : activates only if uses queues the task, or its a dependencyOf

    """

    default      = enum.auto()
    onRegister   = enum.auto()
    reactive     = enum.auto()
    reactiveFail = enum.auto()
    auto         = onRegister

class ExecutionPolicy_e(EnumBuilder_m, enum.Enum):
    """ How the task execution will be ordered
      PRIORITY : Priority Queue with retry, job expansion, dynamic walk of network.
      DEPTH    : No (priority,retry,jobs). basic DFS of the pre-run dependency network
      BREADTH  : No (priority,retry,jobs). basic BFS of the pre-run dependency-network

    """
    PRIORITY = enum.auto() # By Task Priority
    DEPTH    = enum.auto() # Depth First Search
    BREADTH  = enum.auto() # Breadth First Search

    default = PRIORITY

##--|

@runtime_checkable
class TaskTracker_p(Protocol):
    """
    Track tasks that have run, need to run, are running,
    and have failed.
    Does not execute anything itself
    """

    @abstractmethod
    def register_spec(self, *specs:TaskSpec)-> None:
        pass

    @abstractmethod
    def queue_entry(self, name:str|Ident|Concrete[TaskSpec]|Task_p, *, from_user:bool=False, status:Maybe[TaskStatus_e]=None) -> Maybe[Concrete[Ident]]:
        pass

    @abstractmethod
    def get_status(self, task:Concrete[Ident]) -> TaskStatus_e:
        pass

    @abstractmethod
    def set_status(self, task:Concrete[Ident]|Task_p, state:TaskStatus_e) -> bool:
        pass

    @abstractmethod
    def next_for(self, target:Maybe[str|Concrete[Ident]]=None) -> Maybe[Actual]:
        pass

    @abstractmethod
    def build_network(self) -> None:
        pass

    @abstractmethod
    def generate_plan(self, *, policy:Maybe[ExecutionPolicy_e]=None) -> list[PlanEntry]:
        pass

@runtime_checkable
class TaskRunner_p(Protocol):
    """
    Run tasks, actions, and jobs
    """

    @abstractmethod
    def __enter__(self) -> Self:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        pass

    @abstractmethod
    def __init__(self, *, tracker:TaskTracker_p):
        pass

    @abstractmethod
    def __call__(self, *tasks:str) -> bool:
        pass
