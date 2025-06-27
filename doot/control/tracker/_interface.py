#!/usr/bin/env python3
"""

"""
# ruff: noqa:

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import atexit#  for @atexit.register
import collections
import contextlib
import datetime
import enum
import faulthandler
import functools as ftz
import hashlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 1st party imports
from doot.workflow._interface import (ArtifactStatus_e, InjectSpec_i, ActionSpec_i,
                                      RelationSpec_i, Task_i, TaskSpec_i,
                                      TaskStatus_e)

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from jgdv import Maybe, Ident
    from jgdv.structs.chainguard import ChainGuard
    from doot.workflow._interface import Task_i, TaskName_p, Artifact_i, Task_p
    from doot.util.factory._interface import TaskFactory_p, SubTaskFactory_p, DelayedSpec

    type Abstract[T] = T
    type Concrete[T] = T
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class EdgeType_e(enum.Enum):
    """ Enum describing the possible edges of the task tracker's task network """

    TASK              = enum.auto() # task to task
    ARTIFACT_UP       = enum.auto() # abstract to concrete artifact
    ARTIFACT_DOWN     = enum.auto() # concrete to abstract artifact
    TASK_CROSS        = enum.auto() # Task to artifact
    ARTIFACT_CROSS    = enum.auto() # artifact to task

    default           = TASK

    @classmethod
    def artifact_edge_set[T](cls:type) -> set[T]:
        return  {cls.ARTIFACT_UP, cls.ARTIFACT_DOWN, cls.TASK_CROSS} # type: ignore[attr-defined]

# Vars:
MAX_LOOP                        : Final[int]                  = 100

ARTIFACT_EDGES                  : Final[set[EdgeType_e]]      = EdgeType_e.artifact_edge_set()
CLEANUP                         : Final[str]                  = "cleanup"
DECLARE_PRIORITY                : Final[int]                  = 10
EXPANDED                        : Final[str]                  = "expanded"  # Node attribute name
INITIAL_SOURCE_CHAIN_COUNT      : Final[int]                  = 10
MIN_PRIORITY                    : Final[int]                  = -10
REACTIVE_ADD                    : Final[str]                  = "reactive-add"
ROOT                            : Final[str]                  = "root::_.$gen$" # Root node of dependency graph

SUCCESS_STATUSES : Final[set[TaskStatus_e|ArtifactStatus_e]]  = {
    TaskStatus_e.SUCCESS,
    TaskStatus_e.TEARDOWN,
    TaskStatus_e.DEAD,
    ArtifactStatus_e.EXISTS,
}

class ExecutionPolicy_e(enum.Enum):
    """ How the task execution will be ordered
      PRIORITY : Priority Queue with retry, job expansion, dynamic walk of network.
      DEPTH    : No (priority,retry,jobs). basic DFS of the pre-run dependency network
      BREADTH  : No (priority,retry,jobs). basic BFS of the pre-run dependency-network

    """
    PRIORITY = enum.auto() # By Task Priority
    DEPTH    = enum.auto() # Depth First Search
    BREADTH  = enum.auto() # Breadth First Search

    default = PRIORITY

##--| Data

class Registry_d:
    """
    Data used in the registry

    Invariants:
    - every key in tasks has a matching key in specs.
    - every concrete spec is in concrete under its abstract name
    - every implicit task that hasn't been registered is in implicit, mapped to its declaring spec
    """
    type AbsName = Abstract[TaskName_p]
    type ConcName = Concrete[TaskName_p]

    _tracker            : TaskTracker_p

    specs               : dict[TaskName_p, TaskSpec_i]
    concrete            : dict[AbsName, list[ConcName]]
    implicit            : dict[AbsName, TaskName_p]
    tasks               : dict[ConcName, Task_p]
    artifacts           : dict[Artifact_i, set[AbsName]]
    # Artifact sets
    abstract_artifacts  : set[Artifact_i]
    concrete_artifacts  : set[Artifact_i]
    # indirect blocking requirements:
    blockers            : dict[ConcName|Artifact_i, Iterable[RelationSpec_i]]
    late_injections     : dict[ConcName, tuple[InjectSpec_i, TaskName_p]]
    artifact_builders   : dict[Artifact_i, Iterable[TaskName_p]]
    artifact_consumers  : dict[Artifact_i, Iterable[TaskName_p]]

    def __init__(self, *, tracker:TaskTracker_p) -> None:
        self._tracker            = tracker
        self.specs               = {}
        self.concrete            = collections.defaultdict(list)
        self.implicit            = {}
        self.tasks               = {}
        self.artifacts           = collections.defaultdict(set)
        self.abstract_artifacts  = set()
        self.concrete_artifacts  = set()
        self.artifact_builders   = collections.defaultdict(list)
        self.artifact_consumers  = collections.defaultdict(list)
        self.blockers            = collections.defaultdict(list)
        self.late_injections     = {}

##--| components

class Registry_p(Protocol):
    tasks : dict

    def register_spec(self, *specs:TaskSpec_i) -> None: ...

    def instantiate_spec(self, name:Abstract[TaskName_p], *, extra:Maybe[dict|ChainGuard|bool]=None) -> Maybe[Concrete[TaskName_p]]: ...

    def instantiate_relation(self, rel:RelationSpec_i, *, control:Concrete[TaskName_p]) -> Concrete[TaskName_p]: ...

    def make_task(self, name:Concrete[TaskName_p], *, task_obj:Maybe[Task_i]=None, parent:Maybe[Concrete[TaskName_p]]=None) -> Concrete[TaskName_p]: ...

    def verify(self, *, strict:bool=True) -> bool: ...

class Network_p(Protocol):
    _graph      : Any
    _root_node  : TaskName_p
    succ        : Mapping
    pred        : Mapping

    is_valid    : bool

    def build_network(self, *, sources:Maybe[Literal[True]|list[Concrete[TaskName_p]|Artifact_i]]=None) -> None: ...

    def connect(self, left:Concrete[TaskName_p]|Artifact_i, right:Maybe[Literal[False]|Concrete[TaskName_p]|Artifact_i]=None, **kwargs:Any) -> None:  ...

    def validate_network(self, *, strict:bool=True) -> bool:  ...

class Queue_p(Protocol):
    active_set : set[TaskName_p|Artifact_i]

    def queue_entry(self, target:str|TaskName_p|Artifact_i, *, from_user:bool=False, status:Maybe[TaskStatus_e]=None) -> Maybe[Concrete[TaskName_p|Artifact_i]]:  ...

    def deque_entry(self, *, peek:bool=False) -> Concrete[TaskName_p]|Artifact_i: ...

    def clear_queue(self) -> None: ...

##--| Tracker

@runtime_checkable
class TaskTracker_p(Protocol):
    """
    Track tasks that have run, need to run, are running,
    and have failed.
    Does not execute anything itself
    """

    ##--| properties

    @property
    def active(self) -> set[TaskName_p]: ...

    @property
    def specs(self) -> dict[TaskName_p, TaskSpec_i]: ...

    @property
    def artifacts(self) -> dict[Artifact_i, set[Abstract[TaskName_p]]]: ...

    @property
    def tasks(self) -> dict[Concrete[TaskName_p], Task_i]: ...

    @property
    def concrete(self) -> Mapping[Abstract[TaskName_p], list[Concrete[TaskName_p]]]: ...

    @property
    def artifact_builders(self) -> Mapping: ...

    @property
    def abstract_artifacts(self) -> Mapping: ...

    @property
    def concrete_artifacts(self) -> Mapping: ...

    @property
    def network(self) -> Mapping: ...

    @property
    def is_valid(self) -> bool: ...

    @is_valid.setter
    def is_valid(self, val:bool) -> None: ...

    @property
    def injections_remaining(self) -> Mapping: ...

    ##--| public

    def register(self, *specs:TaskSpec_i|Artifact_i|DelayedSpec)-> None: ...

    def queue(self, name:str|Ident|Concrete[TaskSpec_i]|DelayedSpec, *, from_user:bool=False, status:Maybe[TaskStatus_e]=None) -> Maybe[Concrete[Ident]]: ...

    def build(self) -> None: ...

    def plan(self, *, policy:Maybe[ExecutionPolicy_e]=None) -> list[TaskName_p|Artifact_i]: ...

    def next_for(self, target:Maybe[str|Concrete[Ident]]=None) -> Maybe[Concrete[TaskName_p]|Artifact_i]: ...

    ##--| inspection. TODO to remove

    ##--| internal

    @overload
    def _instantiate(self, name:Abstract[TaskName_p], *, extra:Maybe[dict|ChainGuard|bool]=None) -> Maybe[Concrete[TaskName_p]]: ...

    @overload
    def _instantiate(self, rel:RelationSpec_i, *, control:Concrete[TaskName_p]) -> Concrete[TaskName_p]: ...

    @overload
    def _instantiate(self, name:Concrete[TaskName_p], **kwargs:Any) -> Concrete[TaskName_p]: ...

    def _connect(self, left:Concrete[TaskName_p]|Artifact_i, right:Maybe[Literal[False]|Concrete[TaskName_p]|Artifact_i]=None, **kwargs:Any) -> None:  ...

    def _dependency_states_of(self, focus:TaskName_p) -> list[tuple]: ...

    def _successor_states_of(self, focus:TaskName_p) -> list[tuple]: ...

@runtime_checkable
class TaskTracker_i(TaskTracker_p, Protocol):
    _factory            : TaskFactory_p
    _subfactory         : SubTaskFactory_p
    _root_node          : TaskName_p
    _declare_priority   : int
    _min_priority       : int
