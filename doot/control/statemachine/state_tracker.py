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
from doot.control.statemachine.task_network import TaskNetwork
from doot.control.statemachine.task_queue import TaskQueue
from doot.control.statemachine.task_registry import TaskRegistry
from doot.enums import (ArtifactStatus_e, EdgeType_e, LocationMeta_e,
                        QueueMeta_e, RelationMeta_e, TaskMeta_e, TaskStatus_e)
from doot.structs import ActionSpec, TaskArtifact, TaskName, TaskSpec
from doot.task.core.task import DootTask

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, Generic, cast, assert_type, assert_never
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
   type Abstract[T] = T
   type Concrete[T] = T

##--|
from doot._abstract import Task_p, TaskTracker_p
# isort: on
# ##-- end types

##-- logging
logging    = logmod.getLogger(__name__)
printer    = doot.subprinter()
track_l    = doot.subprinter("track")
fail_l     = doot.subprinter("fail")
skip_l     = doot.subprinter("skip")
task_l     = doot.subprinter("task")
artifact_l = doot.subprinter("artifact")
##-- end logging

MAX_LOOP  : Final[int]     = 100

@Proto(TaskTracker_p)
class StateTracker:
    """ The public part of the standard tracker implementation
    Has three components:
    _registry : db for specs and tasks
    _network  : the links between specs in the registry
    _queue    : the logic for determining what task to run next

    """

    def __init__(self):
        self._registry = TaskRegistry()
        self._network  = TaskNetwork(self._registry)
        self._queue    = TaskQueue(self._registry, self._network)

    def register_spec(self, *specs:TaskSpec)-> None:
        self._registry.register_spec(*specs)

    def queue_entry(self, name:str|Concrete[TaskName]|TaskSpec|TaskArtifact|Task_p, *, from_user:bool=False, status:None|TaskStatus_e=None) -> None|Concrete[TaskName|TaskArtifact]:
        # Register or retrieve
        match name:
            case Task_p():
                pass
            case TaskSpec():
                pass
            case TaskArtifact():
                pass
            case TaskName() | str():
                pass

        # Instantiate if necessary
        # Make Task if necessary
        # Insert into Network if necessary
        # Queue
        return self._queue.queue_entry(name, from_user=from_user, status=status)

    def get_status(self, task:Concrete[TaskName]|TaskArtifact) -> TaskStatus_e:
        return self._registry.get_status(task)

    def set_status(self, task:Concrete[TaskName]|TaskArtifact|Task_p, state:TaskStatus_e) -> bool:
        self._registry.set_status(task, state)

    def build_network(self) -> None:
        self._network.build_network()

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

    def next_for(self, target:None|str|TaskName=None) -> None|Task_p|TaskArtifact:
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

        focus : None|str|TaskName|TaskArtifact = None
        count = MAX_LOOP
        result = None
        while (result is None) and bool(self._queue) and 0 < (count:=count-1):
            focus  : TaskName|TaskArtifact = self._queue.deque_entry()
            status : TaskStatus_e          = self._registry.get_status(focus)
            match focus:
                case TaskName():
                    track_l.detail("Tracker Head: %s (Task). State: %s, Priority: %s",
                                  focus, self._registry.get_status(focus), self._registry.tasks[focus].priority)
                case TaskArtifact():
                    track_l.detail("Tracker Head: %s (Artifact). State: %s, Priority: %s",
                                  focus, self._registry.get_status(focus), self._registry.get_status(focus))

            match status:
                case TaskStatus_e.DEAD:
                    track_l.trace("Task is Dead: %s", focus)
                    del self._registry.tasks[focus]
                case TaskStatus_e.DISABLED:
                    track_l.user("Task Disabled: %s", focus)
                case TaskStatus_e.TEARDOWN:
                    track_l.trace("Tearing Down: %s", focus)
                    self._queue.active_set.remove(focus)
                    self._registry.set_status(focus, TaskStatus_e.DEAD)
                    self.propagate_state_and_cleanup(focus)
                case TaskStatus_e.SUCCESS | ArtifactStatus_e.EXISTS:
                    track_l.trace("Task Succeeded: %s", focus)
                    self._queue.execution_trace.append(focus)
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                    heads = [x for x in self._network.succ[focus] if self._network.edges[focus, x].get("job_head", False)]
                    if bool(heads):
                        self.queue_entry(heads[0])
                case TaskStatus_e.FAILED:  # propagate failure
                    self._queue.active_set.remove(focus)
                    fail_l.user("Task Failed, Propagating from: %s to: %s", focus, list(self._network.succ[focus]))
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                    for succ in self._network.succ[focus]:
                        self._registry.set_status(succ, TaskStatus_e.FAILED)
                case TaskStatus_e.HALTED:  # remove and propagate halted status
                    fail_l.user("Task Halted, Propagating from: %s to: %s", focus, list(self._network.succ[focus]))
                    for succ in self._network.succ[focus]:
                        if self._network.edges[focus, succ].get("cleanup", False):
                            continue
                        self.set_status(succ, TaskStatus_e.HALTED)
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                case TaskStatus_e.SKIPPED:
                    skip_l.user("Task was skipped: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.DEAD)
                case TaskStatus_e.RUNNING:
                    track_l.user("Waiting for Runner to update status for: %s", focus)
                    self.queue_entry(focus)
                case TaskStatus_e.READY:   # return the task if its ready
                    track_l.trace("Task Ready to run, informing runner: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.RUNNING)
                    result = self._registry.tasks[focus]
                case TaskStatus_e.WAIT: # Add dependencies of a task to the stack
                    track_l.trace("Checking Task Dependencies: %s", focus)
                    match self._network.incomplete_dependencies(focus):
                        case []:
                            self.queue_entry(focus, status=TaskStatus_e.READY)
                        case [*xs]:
                            track_l.user("Task Blocked: %s on : %s", focus, xs)
                            self.queue_entry(focus)
                            for x in xs:
                                self.queue_entry(x)
                case TaskStatus_e.INIT:
                    track_l.trace("Task Object Initialising: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.WAIT)
                case ArtifactStatus_e.STALE:
                    track_l.user("Artifact is Stale: %s", focus)
                    for pred in self._network.pred[focus]:
                        self.queue_entry(pred)
                case ArtifactStatus_e.DECLARED if bool(focus):
                    self.queue_entry(focus, status=ArtifactStatus_e.EXISTS)
                case ArtifactStatus_e.DECLARED: # Add dependencies of an artifact to the stack
                    match self._network.incomplete_dependencies(focus):
                        case []:
                            assert(not bool(focus))
                            path = focus.expand()
                            self.queue_entry(focus)
                            # Returns the artifact, the runner can try to create it, then override the halt
                            result = focus
                        case [*xs]:
                            track_l.user("Artifact Blocked, queuing producer tasks, count: %s", len(xs))
                            self.queue_entry(focus)
                            for x in xs:
                                self.queue_entry(x)
                case TaskStatus_e.DEFINED:
                    track_l.trace("Constructing Task Object for concrete spec: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.HALTED)
                case TaskStatus_e.DECLARED:
                    track_l.trace("Declared Task dequeued: %s. Instantiating into tracker network.", focus)
                    self.queue_entry(focus)
                case TaskStatus_e.NAMED:
                    track_l.user("A Name only was queued, it has no backing in the tracker: %s", focus)

                case x: # Error otherwise
                    raise doot.errors.TrackingError("Unknown task state: ", x)

        else:
            logging.trace("---- Determined Next Task To Be: %s", result)
            return result


    def generate_plan(self, *args):
        raise NotImplementedError()
