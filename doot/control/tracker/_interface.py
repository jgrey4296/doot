#!/usr/bin/env python3
"""

"""
# ruff: noqa:

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
import collections
import contextlib
import hashlib
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref
import atexit # for @atexit.register
import faulthandler
# ##-- end stdlib imports

from doot.workflow._interface import TaskStatus_e, ArtifactStatus_e, RelationSpec_i

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
    from doot.workflow import TaskSpec, TaskName, TaskArtifact
    from doot.workflow._interface import Task_i

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

    @classmethod # type: ignore
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

##--|

@runtime_checkable
class TaskTracker_p(Protocol):
    """
    Track tasks that have run, need to run, are running,
    and have failed.
    Does not execute anything itself
    """

    ##--| public
    def active(self) -> set[TaskName]: ...
    def register(self, *specs:TaskSpec)-> None: ...

    def queue(self, name:str|Ident|Concrete[TaskSpec], *, from_user:bool=False, status:Maybe[TaskStatus_e]=None) -> Maybe[Concrete[Ident]]: ...

    def get_status(self, task:Concrete[Ident]) -> TaskStatus_e: ...

    def set_status(self, task:Concrete[Ident]|Task_i, state:TaskStatus_e) -> bool: ...

    def build(self) -> None: ...

    def plan(self, *, policy:Maybe[ExecutionPolicy_e]=None) -> list[TaskName|TaskArtifact]: ...

    def next_for(self, target:Maybe[str|Concrete[Ident]]=None) -> Maybe[Concrete[TaskName]|TaskArtifact]: ...

    ##--| internal
    @overload
    def _instantiate(self, name:Abstract[TaskName], *, extra:Maybe[dict|ChainGuard|bool]=None) -> Maybe[Concrete[TaskName]]: ...

    @overload
    def _instantiate(self, rel:RelationSpec_i, *, control:Concrete[TaskName]) -> Concrete[TaskName]: ...

    @overload
    def _instantiate(self, name:Concrete[TaskName], **kwargs:Any) -> Concrete[TaskName]: ...

    def _connect(self, left:Concrete[TaskName]|TaskArtifact, right:Maybe[Literal[False]|Concrete[TaskName]|TaskArtifact]=None, **kwargs:Any) -> None:  ...

    def _get_priority(self, target:Concrete[TaskName|TaskArtifact]) -> int: ...

@runtime_checkable
class TaskTracker_i(TaskTracker_p, Protocol):
    _root_node          : TaskName
    _declare_priority   : int
    _min_priority       : int
    is_valid            : bool
    specs               : dict[TaskName, TaskSpec]
    artifacts           : dict[TaskArtifact, set[Abstract[TaskName]]]
    tasks               : dict[Concrete[TaskName], Task_i]
    artifact_builders   : Mapping
    abstract_artifacts  : Mapping
    concrete_artifacts  : Mapping
    network             : Mapping

##--|

class Registry_p(Protocol):
    tasks : dict

    def register_spec(self, *specs:TaskSpec) -> None: ...

    def instantiate_spec(self, name:Abstract[TaskName], *, extra:Maybe[dict|ChainGuard|bool]=None) -> Maybe[Concrete[TaskName]]: ...

    def instantiate_relation(self, rel:RelationSpec_i, *, control:Concrete[TaskName]) -> Concrete[TaskName]: ...

    def make_task(self, name:Concrete[TaskName], *, task_obj:Maybe[Task_i]=None, parent:Maybe[Concrete[TaskName]]=None) -> Concrete[TaskName]: ...

    def verify(self, *, strict:bool=True) -> bool: ...

class Network_p(Protocol):
    _graph      : Any
    _root_node  : TaskName
    succ        : Mapping
    pred        : Mapping

    is_valid    : bool

    def build_network(self, *, sources:Maybe[Literal[True]|list[Concrete[TaskName]|TaskArtifact]]=None) -> None: ...

    def connect(self, left:Concrete[TaskName]|TaskArtifact, right:Maybe[Literal[False]|Concrete[TaskName]|TaskArtifact]=None, **kwargs:Any) -> None:  ...

    def validate_network(self, *, strict:bool=True) -> bool:  ...

    def incomplete_dependencies(self, focus:Concrete[TaskName]|TaskArtifact) -> list[Concrete[TaskName]|TaskArtifact]: ...

class Queue_p(Protocol):
    active_set : set[TaskName|TaskArtifact]

    @overload
    def queue_entry(self, target:TaskArtifact, *, from_user:bool=False) -> Maybe[Concrete[TaskName|TaskArtifact]]:  ...

    @overload
    def queue_entry(self, target:str|Concrete[TaskName|TaskSpec], *, from_user:bool=False, status:Maybe[TaskStatus_e]=None) -> Maybe[Concrete[TaskName|TaskArtifact]]:  ...

    def deque_entry(self, *, peek:bool=False) -> Concrete[TaskName]|TaskArtifact: ...

    def clear_queue(self) -> None: ...
