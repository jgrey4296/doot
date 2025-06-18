#!/usr/bin/env python3
"""
Abstract Specs: A[n]
Concrete Specs: C[n]
Task:           T[n]

  Expansion: ∀x ∈ C[n].depends_on => A[x] -> C[x]
  Head: C[1].depends_on[A[n].$head$] => A[n] -> C[n], A[n].head -> C[n].head, connect

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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.workflow._interface import ArtifactStatus_e, TaskStatus_e
from doot.workflow import ActionSpec, TaskArtifact, TaskName, TaskSpec, DootTask, RelationSpec, InjectSpec
from .network import TrackNetwork
from .queue import TrackQueue
from .registry import TrackRegistry

# ##-- end 1st party imports

from . import _interface as API # noqa: N812

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
    from networkx import DiGraph

    type Abstract[T] = T
    type Concrete[T] = T

##--|
from doot.workflow._interface import Task_p
from ._interface import TaskTracker_p
# isort: on
# ##-- end types

##-- logging
logging    = logmod.getLogger(__name__)
##-- end logging

##--|

class Tracker_abs:
    """ A public base implementation of most of a tracker
    Has three components:
    _registry : db for specs and tasks
    _network  : the links between specs in the registry
    _queue    : the logic for determining what task to run next

    """
    _register : TrackRegistry
    _network  : TrackNetwork
    _queue    : TrackQueue

    def __init__(self):
        self._registry = TrackRegistry()
        self._network  = TrackNetwork(self._registry)
        self._queue    = TrackQueue(self._registry, self._network)

    ##--| properties
    @property
    def active_set(self) -> set:
        return self._queue.active_set

    @property
    def network(self) -> DiGraph:
        return self._network._graph

    @property
    def _root_node(self) -> TaskName:
        return self._network._root_node

    ##--| dunders
    def __bool__(self) -> bool:
        return bool(self._queue)

    ##--| public
    def register_spec(self, *specs:TaskSpec)-> None:
        self._registry.register_spec(*specs)

    def queue_entry(self, name:str|Concrete[TaskName|TaskSpec]|TaskArtifact, *, from_user:bool=False, status:Maybe[TaskStatus_e]=None, **kwargs:Any) -> Maybe[Concrete[TaskName|TaskArtifact]]:  # noqa: ARG002
        queued = self._queue.queue_entry(name, from_user=from_user, status=status)
        return queued

    def get_status(self, task:Concrete[TaskName]|TaskArtifact) -> TaskStatus_e:
        return self._registry.get_status(task)

    def set_status(self, task:Concrete[TaskName]|TaskArtifact|Task_p, state:TaskStatus_e) -> bool:
        return self._registry.set_status(task, state)

    def build_network(self, *, sources:Maybe[Literal[True]|list[Concrete[TaskName]|TaskArtifact]]=None) -> None:
        self._network.build_network(sources=sources) # type: ignore[attr-defined]

    def validate_network(self) -> None:
        self._network.validate_network() # type: ignore[attr-defined]

    def generate_plan(self, *args:Any) -> list:
        raise NotImplementedError()

    def clear_queue(self) -> None:
        self._queue.clear_queue()



##--|
@Proto(API.TaskTracker_p)
class Tracker(Tracker_abs):

    def next_for(self, target:Maybe[str|TaskName]=None) -> Maybe[Task_p|TaskArtifact]:  # noqa: PLR0912, PLR0915
        """ ask for the next task that can be performed

          Returns a Task or Artifact that needs to be executed or created
          Returns None if it loops too many times trying to find a target,
          or if theres nothing left in the queue

        """
        x       : Any
        focus   : str|TaskName|TaskArtifact
        count   : int
        result  : Maybe[Task_p|TaskArtifact]
        status  : TaskStatus_e

        logging.info("[Next.For] (Active: %s)", len(self._queue.active_set))
        if not self._network.is_valid:
            raise doot.errors.TrackingError("Network is in an invalid state")

        if target and target not in self._queue.active_set:
            self.queue_entry(target, silent=True)

        count  = API.MAX_LOOP
        result = None
        while (result is None) and bool(self._queue) and 0 < (count:=count-1):
            focus   = self._queue.deque_entry()
            status  = self._registry.get_status(focus)
            if focus not in self._queue.active_set:
                continue

            logging.debug("[Next.For.Head]: %s : %s", status, focus)

            match status:
                case TaskStatus_e.DEAD:
                    # Clear state
                    del self._registry.tasks[focus]
                    self._queue.active_set.remove(focus)
                case TaskStatus_e.DISABLED:
                    self._queue.active_set.remove(focus)
                case TaskStatus_e.TEARDOWN:
                    for succ in self._network.succ[focus]:
                        match self.queue_entry(succ):
                            case TaskName() as x if x.is_cleanup():
                                # make the cleanup task early, to apply shared state
                                self._registry._make_task(x, parent=focus)
                            case _:
                                pass
                    else:
                        # TODO for cleanup succ, move focus.state -> succ.state
                        self._registry.set_status(focus, TaskStatus_e.DEAD)
                case ArtifactStatus_e.EXISTS:
                    # TODO artifact Exists, queue its dependents and *don't* add the artifact back in
                    self._queue.execution_trace.append(focus)
                case TaskStatus_e.SUCCESS:
                    self._queue.execution_trace.append(focus)
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                case TaskStatus_e.FAILED:  # propagate failure
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                case TaskStatus_e.HALTED:  # remove and propagate halted status
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                case TaskStatus_e.SKIPPED:
                    self.queue_entry(focus, status=TaskStatus_e.DEAD)
                case TaskStatus_e.RUNNING:
                    self.queue_entry(focus)
                case TaskStatus_e.READY:   # return the task if its ready
                    self.queue_entry(focus, status=TaskStatus_e.RUNNING)
                    result = self._registry.tasks[focus]
                case TaskStatus_e.WAIT: # Add dependencies of a task to the stack
                    match self._network.incomplete_dependencies(focus): # type: ignore[attr-defined]
                        case []:
                            self.queue_entry(focus, status=TaskStatus_e.READY)
                        case [*xs]:
                            logging.debug("Task Blocked: %s on : %s", focus, xs)
                            self.queue_entry(focus)
                            for x in xs:
                                self.queue_entry(x)
                case TaskStatus_e.INIT:
                    task_name = self.queue_entry(focus, status=TaskStatus_e.WAIT)
                case ArtifactStatus_e.STALE:
                    for pred in self._network.pred[focus]:
                        self.queue_entry(pred)
                case ArtifactStatus_e.DECLARED if bool(focus):
                    self.queue_entry(focus, status=ArtifactStatus_e.EXISTS)
                case ArtifactStatus_e.DECLARED: # Add dependencies of an artifact to the stack
                    match self._network.incomplete_dependencies(focus):
                        case [] if not focus.is_concrete():
                            self.queue_entry(focus, status=ArtifactStatus_e.EXISTS)
                        case []:
                            assert(not bool(focus))
                            path = focus.expand()
                            self.queue_entry(focus)
                            # Returns the artifact, the runner can try to create
                            # it, then override the halt
                            result = focus
                        case [*xs]:
                            logging.info("Artifact Blocked, queuing producer tasks, count: %s", len(xs))
                            self.queue_entry(focus)
                            for x in xs:
                                self.queue_entry(x)
                case TaskStatus_e.DEFINED:
                    self.queue_entry(focus, status=TaskStatus_e.HALTED)
                case TaskStatus_e.DECLARED:
                    self._registry._make_task(focus)
                    self.queue_entry(focus)
                case TaskStatus_e.NAMED:
                    logging.warning("A Name only was queued, it has no backing in the tracker: %s", focus)
                case x: # Error otherwise
                    raise doot.errors.TrackingError("Unknown task state", x)

        else:
            logging.info("[Next.For] <- %s", result)
            return result
