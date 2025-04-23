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
from doot._structs.relation_spec import RelationSpec
from doot.control.split_tracker.track_network import TrackNetwork
from doot.control.split_tracker.track_queue import TrackQueue
from doot.control.split_tracker.track_registry import TrackRegistry
from doot.enums import ArtifactStatus_e, TaskStatus_e
from doot.structs import ActionSpec, TaskArtifact, TaskName, TaskSpec
from doot.task.core.task import DootTask

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
from doot._abstract import Task_p, TaskTracker_p
# isort: on
# ##-- end types

##-- logging
logging    = logmod.getLogger(__name__)
##-- end logging

##--|

@Proto(TaskTracker_p)
class SplitTracker:
    """ The public part of the standard tracker implementation
    Has three components:
    _registry : db for specs and tasks
    _network  : the links between specs in the registry
    _queue    : the logic for determining what task to run next

    """

    def __init__(self):
        self._registry = TrackRegistry()
        self._network  = TrackNetwork(self._registry)
        self._queue    = TrackQueue(self._registry, self._network)

    @property
    def active_set(self) -> set:
        return self._queue.active_set

    @property
    def network(self) -> DiGraph:
        return self._network._graph

    @property
    def _root_node(self) -> TaskName:
        return self._network._root_node

    def __bool__(self) -> bool:
        return bool(self._queue)

    def register_spec(self, *specs:TaskSpec)-> None:
        self._registry.register_spec(*specs)

    def queue_entry(self, name:str|Concrete[TaskName|TaskSpec]|TaskArtifact|Task_p, *, from_user:bool=False, status:Maybe[TaskStatus_e]=None) -> Maybe[Concrete[TaskName|TaskArtifact]]:
        # Register
        # Instantiate
        # Make Task
        # Insert into Network
        # Queue
        return self._queue.queue_entry(name, from_user=from_user, status=status)

    def get_status(self, task:Concrete[TaskName]|TaskArtifact) -> TaskStatus_e:
        return self._registry.get_status(task)

    def set_status(self, task:Concrete[TaskName]|TaskArtifact|Task_p, state:TaskStatus_e) -> bool:
        self._registry.set_status(task, state)


    def build_network(self, *, sources:Maybe[True|list[Concrete[TaskName]|TaskArtifact]]=None) -> None:
        self._network.build_network(sources=sources)

    def validate_network(self) -> None:
        self._network.validate_network()

    def propagate_state_and_cleanup(self, name:TaskName) -> None:
        """ Propagate a task's state on to its cleanup task"""
        logging.trace("Queueing Cleanup Task and Propagating State to Cleanup: %s", name)
        cleanups = [x for x in self._network.succ[name] if self._network.edges[name, x].get("cleanup", False)]
        task = self._registry.tasks[name]
        match cleanups:
            case [x, *xs]:
                cleanup_id = self.queue_entry(cleanups[0])
                cleanup_task = self._registry.tasks[cleanup_id]
                cleanup_task.state.update(task.state)
                task.state.clear()
            case _:
                task.state.clear()

    def next_for(self, target:Maybe[str|TaskName]=None) -> Maybe[Task_p|TaskArtifact]:
        """ ask for the next task that can be performed

          Returns a Task or Artifact that needs to be executed or created
          Returns None if it loops too many times trying to find a target,
          or if theres nothing left in the queue

        """
        logging.trace("---- Getting Next Task")
        logging.detail("Tracker Active Set Size: %s", len(self._queue.active_set))
        if not self._network.is_valid:
            raise doot.errors.TrackingError("Network is in an invalid state")

        if target and target not in self._queue.active_set:
            self.queue_entry(target, silent=True)

        focus : Maybe[str|TaskName|TaskArtifact] = None
        count                                    = API.MAX_LOOP
        result : Maybe[Task_p|TaskArtifact]      = None
        while (result is None) and bool(self._queue) and 0 < (count:=count-1):
            focus  : TaskName|TaskArtifact = self._queue.deque_entry()
            status : TaskStatus_e          = self._registry.get_status(focus)
            match focus:
                case TaskName():
                    logging.detail("Tracker Head: %s (Task). State: %s, Priority: %s",
                                   focus, self._registry.get_status(focus), self._registry.tasks[focus].priority)
                case TaskArtifact():
                    logging.detail("Tracker Head: %s (Artifact). State: %s, Priority: %s",
                                   focus, self._registry.get_status(focus), self._registry.get_status(focus))

            match status:
                case TaskStatus_e.DEAD:
                    logging.trace("Task is Dead: %s", focus)
                    del self._registry.tasks[focus]
                case TaskStatus_e.DISABLED:
                    logging.trace("Task Disabled: %s", focus)
                case TaskStatus_e.TEARDOWN:
                    logging.trace("Tearing Down: %s", focus)
                    self._queue.active_set.remove(focus)
                    self._registry.set_status(focus, TaskStatus_e.DEAD)
                    self.propagate_state_and_cleanup(focus)
                case ArtifactStatus_e.EXISTS:
                    # Task Exists, queue its dependents and *don't* add the artifact back in
                    self._queue.execution_trace.append(focus)
                    heads = [x for x in self._network.succ[focus] if self._network.edges[focus, x].get("job_head", False)]
                    if bool(heads):
                        self.queue_entry(heads[0])
                case TaskStatus_e.SUCCESS:
                    logging.trace("Task Succeeded: %s", focus)
                    self._queue.execution_trace.append(focus)
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                    heads = [x for x in self._network.succ[focus] if self._network.edges[focus, x].get("job_head", False)]
                    if bool(heads):
                        self.queue_entry(heads[0])
                case TaskStatus_e.FAILED:  # propagate failure
                    self._queue.active_set.remove(focus)
                    logging.user("Task Failed, Propagating from: %s to: %s", focus, list(self._network.succ[focus]))
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                    for succ in self._network.succ[focus]:
                        self._registry.set_status(succ, TaskStatus_e.FAILED)
                case TaskStatus_e.HALTED:  # remove and propagate halted status
                    logging.user("Task Halted, Propagating from: %s to: %s", focus, list(self._network.succ[focus]))
                    for succ in self._network.succ[focus]:
                        if self._network.edges[focus, succ].get("cleanup", False):
                            continue
                        self.set_status(succ, TaskStatus_e.HALTED)
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                case TaskStatus_e.SKIPPED:
                    logging.user("Task was skipped: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.DEAD)
                case TaskStatus_e.RUNNING:
                    logging.trace("Waiting for Runner to update status for: %s", focus)
                    self.queue_entry(focus)
                case TaskStatus_e.READY:   # return the task if its ready
                    logging.trace("Task Ready to run, informing runner: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.RUNNING)
                    result = self._registry.tasks[focus]
                case TaskStatus_e.WAIT: # Add dependencies of a task to the stack
                    logging.trace("Checking Task Dependencies: %s", focus)
                    match self._network.incomplete_dependencies(focus):
                        case []:
                            self.queue_entry(focus, status=TaskStatus_e.READY)
                        case [*xs]:
                            logging.user("Task Blocked: %s on : %s", focus, xs)
                            self.queue_entry(focus)
                            for x in xs:
                                self.queue_entry(x)
                case TaskStatus_e.INIT:
                    logging.trace("Task Object Initialising: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.WAIT)
                case ArtifactStatus_e.STALE:
                    logging.user("Artifact is Stale: %s", focus)
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
                            # Returns the artifact, the runner can try to create it, then override the halt
                            result = focus
                        case [*xs]:
                            logging.trace("Artifact Blocked, queuing producer tasks, count: %s", len(xs))
                            self.queue_entry(focus)
                            for x in xs:
                                self.queue_entry(x)
                case TaskStatus_e.DEFINED:
                    logging.trace("Constructing Task Object for concrete spec: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.HALTED)
                case TaskStatus_e.DECLARED:
                    logging.trace("Declared Task dequeued: %s. Instantiating into tracker network.", focus)
                    self.queue_entry(focus)
                case TaskStatus_e.NAMED:
                    logging.user("A Name only was queued, it has no backing in the tracker: %s", focus)

                case x: # Error otherwise
                    raise doot.errors.TrackingError("Unknown task state: ", x)

        else:
            logging.trace("---- Determined Next Task To Be: %s", result)
            return result

    def generate_plan(self, *args):
        raise NotImplementedError()

    def clear_queue(self):
        self._queue.clear_queue()
