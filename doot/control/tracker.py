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
from collections import defaultdict
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Literal, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

import networkx as nx

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import (FailPolicy_p, Job_i, Task_i, TaskRunner_i,
                            TaskTracker_i)
from doot.control.base_tracker import EDGE_E, MIN_PRIORITY, ROOT, BaseTracker
from doot.enums import TaskStatus_e, ExecutionPolicy_e
from doot.structs import (DootCodeReference, DootTaskArtifact, DootTaskName,
                          DootTaskSpec)
from doot.task.base_task import DootTask

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

Node      : TypeAlias      = DootTaskName|DootTaskArtifact
Depth     : TypeAlias      = int
PlanEntry : TypeAlias      = tuple[Depth, Node, str]

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


    def _dfs_plan(self) -> list[PlanEntry]:
        """ Generates the Execution plan of queued tasks,
          as a list of the edges it will move through.
          not taking into account priority or status.
        """
        # Reversed because directed graphs expect a graph in the other direction.
        # but that would make a tasks dependencies 'successors',
        # which is confusing for a dependency network
        plan  : list[PlanEntry]      = []
        stack : list[PlanEntry]      = [(0, x, "Initial Task") for x in self.network.pred[self._root_node]]
        found_count                                = defaultdict(lambda: 0)
        while bool(stack):
            depth, node, desc = stack[-1]
            node_type = "Branch" if bool(self.network.pred[node]) else "Leaf"
            match found_count[node]:
                case 0:
                    found_count[node] += 1
                    plan.append((depth, node, f"{depth}: Enter {node_type} {desc}: {node.readable}"))
                    stack += [(depth+1, x, "Dependency") for x in self.network.pred[node]]
                case 1: # exit
                    found_count[node] += 1
                    if node_type != "Leaf":
                        plan.append((depth, node, f"{depth}: Exit {node_type} {desc}: {node.readable}"))
                    stack.pop()
                    pass
                case _: # error
                    stack.pop()

        return plan

    def _bfs_plan(self) -> list[PlanEntry]:
        """ Generates the Execution plan of queued tasks,
          as a list of the edges it will move through.
          not taking into account priority or status.
        """
        # Reversed because directed graphs expect a graph in the other direction.
        # but that would make a tasks dependencies 'successors',
        # which is confusing for a dependency network
        plan  : list[PlanEntry]      = []
        queue : list[PlanEntry]      = [(0, x, "Initial Task") for x in self.network.pred[self._root_node]]
        found_count                  = defaultdict(lambda: 0)
        while bool(queue):
            depth, node, desc = queue.pop(0)
            node_type = "Branch" if bool(self.network.pred[node]) else "Leaf"
            match found_count[node]:
                case 0:
                    found_count[node] += 1
                    plan.append((depth, node, f"{depth}: Enter {node_type} {desc}: {node.readable}"))
                    queue += [(depth+1, x, "Dependency") for x in self.network.pred[node]]
                    queue += [(depth, node, desc)]
                case 1: # exit
                    if all(found_count[y] > 1 for y in self.network.pred[node]):
                        found_count[node] += 1

                    queue += [(depth, node, desc)]

                case 2:
                    found_count[node] += 1
                    plan.append((depth, node, f"{depth}: Exit {node_type} {desc}: {node.readable}"))

                case _: # error
                    pass



        return plan

    def _priority_plan(self) -> list[PlanEntry]:
        raise NotImplementedError()

    def generate_plan(self, *, policy:None|ExecutionPolicy_e=None) -> list[PlanEntry]:
        match policy:
            case None | ExecutionPolicy_e.DEPTH:
                 return self._dfs_plan()
            case ExecutionPolicy_e.BREADTH:
                return self._bfs_plan()
            case ExecutionPolicy_e.PRIORITY:
                return self._priority_plan()



    def write(self, target:pl.Path):
        """ Write the task network out as jsonl  """
        raise NotImplementedError()

    def next_for(self, target:None|str|DootTaskName=None) -> None|Task_i|DootTaskArtifact:
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
                case TaskStatus_e.DEAD:
                    logging.warning("Task is Dead: %s", focus)
                case TaskStatus_e.DISABLED:
                    logging.info("Task Disabled: %s", focus)
                case TaskStatus_e.TEARDOWN:
                    logging.info("Tearing Down: %s", focus)
                    self.active_set.remove(focus)
                    self.set_status(focus, TaskStatus_e.DEAD)
                case TaskStatus_e.SUCCESS | TaskStatus_e.EXISTS:
                    logging.info("Task Succeeded: %s", focus)
                    self.execution_trace.append(focus)
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                    for succ in [x for x in self.network.succ[focus] if self.get_status(x) ]:
                        if nx.has_path(self.network, focus, succ):
                            self.queue_entry(succ)

                    # TODO self._reactive_queue(focus)

                case TaskStatus_e.FAILED:  # propagate failure
                    self.active_set.remove(focus)
                    printer.warning("Task Failed, Propagating from: %s to: %s", focus, list(self.network.succ[focus]))
                    for succ in self.network.succ[focus]:
                        self.set_status(succ, TaskStatus_e.FAILED)
                case TaskStatus_e.HALTED:  # remove and propagate halted status
                    self.active_set.remove(focus)
                    printer.warning("Task Halted, Propagating from: %s to: %s", focus, list(self.network.succ[focus]))
                    for succ in self.network.succ[focus]:
                        self.set_status(succ, TaskStatus_e.HALTED)
                case TaskStatus_e.SKIPPED:
                    logging.info("Task was skipped: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                case TaskStatus_e.RUNNING:
                    printer.info("Awaiting Runner to update status for: %s", focus)
                    self.queue_entry(focus)
                case TaskStatus_e.READY:   # return the task if its ready
                    logging.info("Task Ready to run, informing runner: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.RUNNING)
                    return self.tasks[focus]

                case TaskStatus_e.WAIT: # Add dependencies of a task to the stack
                    logging.info("Checking Task Dependencies: %s", focus)
                    match self.incomplete_dependencies(focus):
                        case []:
                            self.queue_entry(focus, status=TaskStatus_e.READY)
                        case [*xs]:
                            logging.info("Task Blocked: %s on : %s", focus, xs)
                            self.queue_entry(focus)
                            for x in xs:
                                self.queue_entry(x)
                case TaskStatus_e.INIT:
                    logging.info("Task Object Initialising")
                    self.queue_entry(focus, status=TaskStatus_e.WAIT)

                case TaskStatus_e.STALE:
                    logging.info("Artifact is Stale: %s", focus)
                    for pred in self.network.pred[focus]:
                        self.queue_entry(pred)
                case TaskStatus_e.ARTIFACT: # Add dependencies of an artifact to the stack
                    match self.incomplete_dependencies(focus):
                        case [] if bool(focus):
                            self.queue_entry(focus, status=TaskStatus_e.EXISTS)
                        case []:
                            path = doot.locs[focus.path]
                            logging.warning("An Artifact has no incomplete dependencies, yet doesn't exist: %s (expanded: %s : exists: %s)", focus, path, path.exists())
                            self.queue_entry(focus, status=TaskStatus_e.HALTED)
                        case [*xs]:
                            logging.info("Artifact Blocked, queuing producer tasks, count: %s", len(xs))
                            self.queue_entry(focus)
                            for x in xs:
                                self.queue_entry(x)
                case TaskStatus_e.DEFINED:
                    logging.info("Constructing Task Object for concrete spec: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.HALTED)
                case TaskStatus_e.DECLARED:
                    logging.info("Declared Task dequeued: %s. Instantiating into tracker network.", focus)
                    self.queue_entry(focus)
                case TaskStatus_e.NAMED:
                    logging.warning("A Name only was queued, it has no backing in the tracker: %s", focus)

                case x: # Error otherwise
                    raise doot.errors.DootTaskTrackingError("Unknown task state: ", x)

        return None
