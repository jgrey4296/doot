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
    from doot.workflow._interface import Task_i, TaskName_p, Artifact_i

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

##--| Factories

@runtime_checkable
class TaskFactory_p(Protocol):

    def __init__(self, *, spec_ctor:Maybe[type]=None, task_ctor:Maybe[type]=None, job_ctor:Maybe[type]=None): ...

    def build(self, data:ChainGuard|dict|TaskName_p|str) -> TaskSpec_i: ...

    def instantiate(self, obj:TaskSpec_i, *, extra:Maybe[Mapping|bool]=None) -> TaskSpec_i: ...

    def reify_partial(self, obj:TaskSpec_i, actual:TaskSpec_i) -> TaskSpec_i: ...

    def over(self, obj:TaskSpec_i, data:TaskSpec_i, suffix:Maybe[str|Literal[False]]=None) -> TaskSpec_i: ...

    def under(self, obj:TaskSpec_i, data:dict|TaskSpec_i, suffix:Maybe[str|Literal[False]]=None) -> TaskSpec_i: ...

    def make(self, obj:TaskSpec_i, *, ensure:Maybe=None, inject:Maybe[tuple[InjectSpec_i, Task_i]]=None, parent:Maybe[Task_i]=None) -> Task_i:  ...

    def action_group_elements(self, obj:TaskSpec_i) -> Iterable[ActionSpec_i|RelationSpec_i]: ...

@runtime_checkable
class SubTaskFactory_p(Protocol):

    def generate_names(self, obj:TaskSpec_i) -> list[TaskName_p]: ...

    def generate_specs(self, obj:TaskSpec_i) -> list[dict]: ...

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

    def incomplete_dependencies(self, focus:Concrete[TaskName_p]|Artifact_i) -> list[Concrete[TaskName_p]|Artifact_i]: ...

class Queue_p(Protocol):
    active_set : set[TaskName_p|Artifact_i]

    @overload
    def queue_entry(self, target:Artifact_i, *, from_user:bool=False) -> Maybe[Concrete[TaskName_p|Artifact_i]]:  ...

    @overload
    def queue_entry(self, target:str|Concrete[TaskName_p|TaskSpec_i], *, from_user:bool=False, status:Maybe[TaskStatus_e]=None) -> Maybe[Concrete[TaskName_p|Artifact_i]]:  ...

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

    ##--| public

    def active(self) -> set[TaskName_p]: ...

    def register(self, *specs:TaskSpec_i)-> None: ...

    def queue(self, name:str|Ident|Concrete[TaskSpec_i], *, from_user:bool=False, status:Maybe[TaskStatus_e]=None) -> Maybe[Concrete[Ident]]: ...

    def get_status(self, task:Concrete[TaskName_p|Ident]) -> TaskStatus_e: ...

    def set_status(self, task:Concrete[TaskName_p|Ident]|Task_i, state:TaskStatus_e) -> bool: ...

    def build(self) -> None: ...

    def plan(self, *, policy:Maybe[ExecutionPolicy_e]=None) -> list[TaskName_p|Artifact_i]: ...

    def next_for(self, target:Maybe[str|Concrete[Ident]]=None) -> Maybe[Concrete[TaskName_p]|Artifact_i]: ...

    ##--| internal

    @overload
    def _instantiate(self, name:Abstract[TaskName_p], *, extra:Maybe[dict|ChainGuard|bool]=None) -> Maybe[Concrete[TaskName_p]]: ...

    @overload
    def _instantiate(self, rel:RelationSpec_i, *, control:Concrete[TaskName_p]) -> Concrete[TaskName_p]: ...

    @overload
    def _instantiate(self, name:Concrete[TaskName_p], **kwargs:Any) -> Concrete[TaskName_p]: ...

    def _connect(self, left:Concrete[TaskName_p]|Artifact_i, right:Maybe[Literal[False]|Concrete[TaskName_p]|Artifact_i]=None, **kwargs:Any) -> None:  ...

    def _get_priority(self, target:Concrete[TaskName_p|Artifact_i]) -> int: ...

@runtime_checkable
class TaskTracker_i(TaskTracker_p, Protocol):
    _factory            : TaskFactory_p
    _subfactory         : SubTaskFactory_p
    _root_node          : TaskName_p
    _declare_priority   : int
    _min_priority       : int
    is_valid            : bool
    specs               : dict[TaskName_p, TaskSpec_i]
    artifacts           : dict[Artifact_i, set[Abstract[TaskName_p]]]
    tasks               : dict[Concrete[TaskName_p], Task_i]
    artifact_builders   : Mapping
    abstract_artifacts  : Mapping
    concrete_artifacts  : Mapping
    network             : Mapping
