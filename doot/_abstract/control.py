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
from abc import abstractmethod
from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Literal, Mapping, Match,
                    MutableMapping, NewType, Protocol, Sequence, Tuple,
                    TypeAlias, TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

from jgdv.enums.util import EnumBuilder_m, FlagsBuilder_m

# ##-- 1st party imports
from doot._abstract.protocols import ArtifactStruct_p, SpecStruct_p
from doot._abstract.reporter import Reporter_p
from doot._abstract.task import Task_i
# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# ## Types
AbstractId                     : TypeAlias                   = "TaskName|TaskArtifact"
ConcreteId                     : TypeAlias                   = "TaskName|TaskArtifact"
AnyId                          : TypeAlis                    = "TaskName|TaskArtifact"
AbstractSpec                   : TypeAlias                   = "TaskSpec"
ConcreteSpec                   : TypeAlias                   = "TaskSpec"
AnySpec                        : TypeAlias                   = "TaskSpec"
Depth                          : TypeAlias                   = int
PlanEntry                      : TypeAlias                   = tuple[Depth, ConcreteId, str]

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
    def artifact_edge_set(cls):
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

class TaskTracker_i:
    """
    Track tasks that have run, need to run, are running,
    and have failed.
    Does not execute anything itself
    """

    @abstractmethod
    def register_spec(self, *specs:AnySpec)-> None:
        pass

    @abstractmethod
    def queue_entry(self, name:str|AnyId|ConcreteSpec|Task_i, *, from_user:bool=False, status:None|TaskStatus_e=None) -> None|Node:
        pass

    @abstractmethod
    def get_status(self, task:ConcreteId) -> TaskStatus_e:
        pass

    @abstractmethod
    def set_status(self, task:ConcreteId|Task_i, state:TaskStatus_e) -> bool:
        pass

    @abstractmethod
    def next_for(self, target:None|str|ConcreteId=None) -> None|Task_i|"TaskArtifact":
        pass

    @abstractmethod
    def build_network(self) -> None:
        pass

    @abstractmethod
    def generate_plan(self, *, policy:None|ExecutionPolicy_e=None) -> list[PlanEntry]:
        pass

class TaskRunner_i:
    """
    Run tasks, actions, and jobs
    """

    @abstractmethod
    def __enter__(self) -> Any:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        pass

    @abstractmethod
    def __init__(self, *, tracker:TaskTracker_i, reporter:Reporter_p):
        pass

    @abstractmethod
    def __call__(self, *tasks:str) -> bool:
        pass
