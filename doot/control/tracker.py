#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
# import abc
# import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from collections import defaultdict
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Literal, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import (FailPolicy_p, Job_i, Task_i, TaskRunner_i,
                            TaskTracker_i)
from doot.control.base_tracker import EDGE_E, MIN_PRIORITY, ROOT, BaseTracker
from doot.enums import TaskStatus_e
from doot.structs import (DootCodeReference, DootTaskArtifact, DootTaskName,
                          DootTaskSpec)
from doot.task.base_task import DootTask

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

@doot.check_protocol
class DootTracker(BaseTracker, TaskTracker_i):
    """
    track dependencies in a networkx digraph,
    predecessors of a node are its dependencies.
      ie: SubDependency -> Dependency -> Task -> ROOT

    tracks definite and indefinite artifacts as products and dependencies of tasks as well.

    the `network` stores nodes as full names of tasks
    """

    def __init__(self, shadowing:bool=False):
        super().__init__()
        self.shadowing = False

    def dfs_dag(self) -> list[DootTaskName]:
        raise NotImplementedError()

    def bfs_dag(self) -> list[DootTaskName]:
        raise NotImplementedError()

    def write(self, target:pl.Path):
        # DFS or BFS the dag
        # write out as jsonl
        raise NotImplementedError()

    def next_for(self, target:None|DootTaskName|str=None) -> None|Task_i|DootTaskArtifact:
        """ ask for the next task that can be performed """
        if not self.network_is_valid:
            raise doot.errors.DootTaskTrackingError("Network is in an invalid state")

        if target and target not in self.active_set:
            self.queue_entry(target, silent=True)

        focus : None|str|DootTaskName|DootTaskArtifact = None
        while bool(self):
            focus  : DootTaskName|DootTaskArtifact = self.deque_entry()
            status : TaskStatus_e                  = self.get_status(focus)
            match focus:
                case DootTaskName():
                    logging.debug("Tracker Head: %s (Task). State: %s, Priority: %s", focus, self.get_status(focus), self.tasks[focus].priority)
                case DootTaskArtifact():
                    logging.debug("Tracker Head: %s (Artifact). State: %s, Priority: %s", focus, self.get_status(focus), self._artifact_status[focus])

            logging.debug("Tracker Active Set: %s", self.active_set)

            match status:
                case TaskStatus_e.SUCCESS | TaskStatus_e.EXISTS:
                    self.execution_trace.append(focus)
                    self.active_set.remove(focus)
                    # TODO self._reactive_queue(focus)
                    for succ in self.network.succ[focus]:
                        self.queue_entry(succ)

                case TaskStatus_e.HALTED:  # remove and propagate halted status
                    self.active_set.remove(focus)
                    printer.warning("Propagating Halt from: %s to: %s", focus, list(self.network.succ[focus]))
                    for pred in self.network.succ[focus]:
                        self.set_status(pred, TaskStatus_e.HALTED)
                case TaskStatus_e.FAILED:  # propagate failure
                    self.active_set.remove(focus)
                    printer.warning("Propagating Failure from: %s to: %s", focus, list(self.network.succ[focus]))
                    for pred in self.network.succ[focus]:
                        self.set_status(pred, TaskStatus_e.FAILED)
                case TaskStatus_e.RUNNING:
                    raise doot.errors.DootTaskTrackingError("running state shouldn't be possible")

                case TaskStatus_e.READY if focus in self.execution_trace: # error on running the same task twice
                    raise doot.errors.DootTaskTrackingError("Task Attempted to run twice: %s", focus)

                case TaskStatus_e.READY:   # return the task if its ready
                    self.queue_entry(focus)
                    return self.tasks[focus]

                case TaskStatus_e.ARTIFACT: # Add dependencies of an artifact to the stack
                    match self.incomplete_dependencies(focus):
                        case [] if bool(focus):
                            self.set_status(focus, TaskStatus_e.EXISTS)
                        case []:
                            path = doot.locs[focus.path]
                            logging.warning("An Artifact has no incomplete dependencies, yet doesn't exist: %s (expanded: %s : exists: %s)", focus, path, path.exists())
                            self.set_status(focus, TaskStatus_e.HALTED)
                            self.queue_entry(focus)
                        case [*xs]:
                            logging.info("Artifact Blocked, queuing it's producer tasks: count %s", len(xs))
                            self.queue_entry(focus)
                            for x in xs:
                                self.queue_entry(x)
                case TaskStatus_e.WAIT: # Add dependencies of a task to the stack
                    match self.incomplete_dependencies(focus):
                        case []:
                            self.set_status(focus, TaskStatus_e.READY)
                            self.queue_entry(focus)
                        case [*xs]:
                            logging.info("Task Blocked: %s on : %s", focus, xs)
                            self.queue_entry(focus)
                            for x in xs:
                                self.queue_entry(x)
                case TaskStatus_e.DEFINED:
                    # is in the network, but not built as a task
                    logging.warning("Managed to get the status of a task that hasn't been built", focus)
                    self.set_status(focus, TaskStatus_e.HALTED)
                    self.queue_entry(focus)
                case TaskStatus_e.DECLARED:
                    logging.warning("Tried to Schedule a Declared but Undefined Task: %s", focus)
                    if self.tasks[focus].priority <= MIN_PRIORITY:
                        self.set_status(focus, TaskStatus_e.SUCCESS)

                    self.queue_entry(focus)

                case x: # Error otherwise
                    raise doot.errors.DootTaskTrackingError("Unknown task state: ", x)

        return None
