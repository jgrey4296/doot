#!/usr/bin/env python3
"""
Abstract Specs: A[n]
Concrete Specs: C[n]
Task:           T[n]

  Expansion: ∀x ∈ C[n].depends_on => A[x] -> C[x]
  Head: C[1].depends_on[A[n].$head$] => A[n] -> C[n], A[n].head -> C[n].head, connect

See EOF for license/metadata/notes as applicable
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
import weakref
from collections import defaultdict
from itertools import chain, cycle

from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Self,
                    MutableMapping, Protocol, Sequence, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import FailPolicy_p, Job_i, Task_i, TaskRunner_i, TaskTracker_i
from doot._structs.relation_spec import RelationSpec
from doot.enums import TaskMeta_f, QueueMeta_e, TaskStatus_e, LocationMeta_f, RelationMeta_e, EdgeType_e
from doot.structs import (ActionSpec, TaskArtifact,
                          TaskName, TaskSpec)
from doot.task.base_task import DootTask

from doot.control.statemachine.task_registry import TaskRegistry
from doot.control.statemachine.task_network import TaskNetwork
from doot.control.statemachine.task_queue import TaskQueue
# ##-- end 1st party imports

##-- logging
logging    = logmod.getLogger(__name__)
printer    = doot.subprinter()
track_l    = doot.subprinter("track")
logging.disabled = True
##-- end logging

ConcreteId                     : TypeAlias                   = TaskName|TaskArtifact
AnyId                          : TypeAlias                   = TaskName|TaskArtifact
ConcreteSpec                   : TypeAlias                   = TaskSpec
AnySpec                        : TypeAlias                   = TaskSpec

class StateTracker(TaskTracker_i):
    """ The public part of the standard tracker implementation """

    def __init__(self):
        self._registry = TaskRegistry()
        self._network  = TaskNetwork()
        self._queue    = TaskQueue()

    def register_spec(self, *specs:AnySpec)-> None:
        self._registry.register_spec(*specs)

    def queue_entry(self, name:str|AnyId|ConcreteSpec|Task_i, *, from_user:bool=False, status:None|TaskStatus_e=None) -> None|ConcreteId:
        # Register
        # Instantiate
        # Make Task
        # Insert into Network
        # Queue
        return self._queue.queue_entry(name, from_user=from_user, status=status)

    def get_status(self, task:ConcreteId) -> TaskStatus_e:
        return self._registry.get_status(task)

    def set_status(self, task:ConcreteId|Task_i, state:TaskStatus_e) -> bool:
        self._registry.set_status(task)

    def build_network(self) -> None:
        self._network.build_network()
