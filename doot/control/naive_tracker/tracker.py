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
import re
import time
from collections import defaultdict
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto, Mixin
import networkx as nx
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.enums import EdgeType_e, ExecutionPolicy_e, TaskStatus_e, TaskMeta_e, ArtifactStatus_e
from doot.structs import TaskArtifact, TaskName, TaskSpec
from doot.task.core.task import DootTask

from doot.control.naive_tracker._core import BaseTracker

# ##-- end 1st party imports

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
    from jgdv import Maybe, Depth
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    import pathlib as pl
    type Node      = TaskName|TaskArtifact
    type PlanEntry = tuple[Depth, Node, str]

##--|
from doot._abstract import (Task_p, TaskTracker_p)
# isort: on
# ##-- end types

##-- logging
logging    = logmod.getLogger(__name__)
##-- end logging

MAX_LOOP  : Final[int]     = 100
##--|
class TrackerPersistence_m:
    """ Mixin for persisting the tracker """

    def write(self, target:pl.Path) -> None:
        """ Write the task network out as jsonl  """
        raise NotImplementedError()

    def read(self, target:pl.Path) -> None:
        raise NotImplementedError()

class TrackerPlanGen_m:
    """ Mixin for generating plans """

    def _dfs_plan(self) -> list[PlanEntry]:
        """ Generates the Execution plan of queued tasks,
          as a list of the edges it will move through.
          not taking into account priority or status.
        """
        logging.trace("Generating DFS Plan")
        plan  : list[PlanEntry]      = []
        # Reverse the sort because its a stack
        stack : list[PlanEntry]      = [(0, x, "Initial Task") for x in sorted(self.network.pred[self._root_node], key=NaiveTracker._node_sort, reverse=True)]
        found_count                                = defaultdict(lambda: 0)
        logging.detail("Initial DFS Stack: %s", stack)
        while bool(stack):
            depth, node, desc = stack[-1]
            node_type = "Branch" if bool(self.network.pred[node]) else "Leaf"
            match found_count[node]:
                case 0:
                    found_count[node] += 1
                    plan.append((depth, node, f"{depth}: Enter {node_type} {desc}: {node.readable}"))
                    stack += [(depth+1, x, "Dependency") for x in sorted(self.network.pred[node], key=NaiveTracker._node_sort, reverse=True)]
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
        logging.trace("Generating BFS Plan")
        plan  : list[PlanEntry]      = []
        queue : list[PlanEntry]      = [(0, x, "Initial Task") for x in sorted(self.network.pred[self._root_node], key=NaiveTracker._node_sort)]
        found_count                  = defaultdict(lambda: 0)
        logging.detail("Initial BFS Queue: %s", queue)
        while bool(queue):
            depth, node, desc = queue.pop(0)
            node_type = "Branch" if bool(self.network.pred[node]) else "Leaf"
            match found_count[node]:
                case 0:
                    found_count[node] += 1
                    plan.append((depth, node, f"{depth}: Enter {node_type} {desc}: {node.readable}"))
                    queue += [(depth+1, x, "Dependency") for x in sorted(self.network.pred[node], key=NaiveTracker._node_sort)]
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
        """ Runs the tracker in actual, until no more queued tasks.
          Pretends that all tasks/artifacts result in success
          Does not expand jobs

          Afterwards, restores the original state of the queue, and artifacts,
          then re-queues original tasks
          """
        raise NotImplementedError()

    def generate_plan(self, *, policy:Maybe[ExecutionPolicy_e]=None) -> list[PlanEntry]:
        """ Generate an ordered list of tasks that would be executed.
          Does not expand jobs.
          """
        logging.trace("---- Generating Plan")
        match policy:
            case None | ExecutionPolicy_e.DEPTH:
                 return self._dfs_plan()
            case ExecutionPolicy_e.BREADTH:
                return self._bfs_plan()
            case ExecutionPolicy_e.PRIORITY:
                return self._priority_plan()
            case _:
                raise doot.errors.TrackingError("Unknown plan generation form", policy)

##--|

@Proto(TaskTracker_p)
@Mixin(TrackerPersistence_m, TrackerPlanGen_m)
class NaiveTracker(BaseTracker):
    """
    track dependencies in a networkx digraph,
    predecessors of a node are its dependencies.
      ie: SubDependency -> Dependency -> Task -> ROOT

    tracks definite and indefinite artifacts as products and dependencies of tasks as well.

    the `network` stores nodes as full names of tasks
    """
    _node_sort : ClassVar[callable] = lambda x: str(x)

    def __init__(self, shadowing:bool=False):
        super().__init__()
        self.shadowing = False

    def propagate_state_and_cleanup(self, name:TaskName) -> None:
        """ Propagate a task's state on to its cleanup task"""
        logging.detail("Queueing Cleanup Task and Propagating State to Cleanup: %s", name)
        cleanups = [x for x in self.network.succ[name] if self.network.edges[name, x].get("cleanup", False)]
        task = self.tasks[name]
        match cleanups:
            case [x, *xs]:
                cleanup_id = self.queue_entry(cleanups[0])
                cleanup_task = self.tasks[cleanup_id]
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
        logging.detail("Tracker Active Set Size: %s", len(self.active_set))
        if not self.network_is_valid:
            raise doot.errors.TrackingError("Network is in an invalid state")

        if target and target not in self.active_set:
            self.queue_entry(target, silent=True)

        focus : None|str|TaskName|TaskArtifact = None
        count = MAX_LOOP
        result = None
        while (result is None) and bool(self) and 0 < (count:=count-1):
            focus  : TaskName|TaskArtifact = self.deque_entry()
            status : TaskStatus_e          = self.get_status(focus)
            match focus:
                case TaskName():
                    logging.trace("Tracker Head: %s (Task). State: %s, Priority: %s", focus, self.get_status(focus), self.tasks[focus].priority)
                case TaskArtifact():
                    logging.trace("Tracker Head: %s (Artifact). State: %s, Priority: %s", focus, self.get_status(focus), self._artifact_status[focus])

            match status:
                case TaskStatus_e.DEAD:
                    logging.detail("Task is Dead: %s", focus)
                    del self.tasks[focus]
                case TaskStatus_e.DISABLED:
                    doot.report.user("Task Disabled: %s", focus)
                    logging.detail("Task Disabled: %s", focus)
                case TaskStatus_e.TEARDOWN:
                    logging.detail("Tearing Down: %s", focus)
                    self.active_set.remove(focus)
                    self.set_status(focus, TaskStatus_e.DEAD)
                    self.propagate_state_and_cleanup(focus)
                case ArtifactStatus_e.EXISTS:
                    # Task Exists, queue its dependents and *don't* add the artifact back in
                    self.execution_trace.append(focus)
                    heads = [x for x in self.network.succ[focus] if self.network.edges[focus, x].get("job_head", False)]
                    if bool(heads):
                        self.queue_entry(heads[0])
                case TaskStatus_e.SUCCESS:
                    logging.detail("Task Succeeded: %s", focus)
                    self.execution_trace.append(focus)
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                    heads = [x for x in self.network.succ[focus] if self.network.edges[focus, x].get("job_head", False)]
                    if bool(heads):
                        self.queue_entry(heads[0])
                case TaskStatus_e.FAILED:  # propagate failure
                    self.active_set.remove(focus)
                    doot.report.user("Task Failed, Propagating from: %s to: %s", focus, list(self.network.succ[focus]))
                    logging.detail("Task Failed, Propagating from: %s to: %s", focus, list(self.network.succ[focus]))
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                    for succ in self.network.succ[focus]:
                        self.set_status(succ, TaskStatus_e.FAILED)
                case TaskStatus_e.HALTED:  # remove and propagate halted status
                    doot.report.user("Task Halted, Propagating from: %s to: %s", focus, list(self.network.succ[focus]))
                    logging.detail("Task Halted, Propagating from: %s to: %s", focus, list(self.network.succ[focus]))
                    for succ in self.network.succ[focus]:
                        if self.network.edges[focus, succ].get("cleanup", False):
                            continue
                        self.set_status(succ, TaskStatus_e.HALTED)
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                case TaskStatus_e.SKIPPED:
                    logging.user("Task was skipped: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.DEAD)
                case TaskStatus_e.RUNNING:
                    logging.detail("Waiting for Runner to update status for: %s", focus)
                    self.queue_entry(focus)
                case TaskStatus_e.READY:   # return the task if its ready
                    logging.detail("Task Ready to run, informing runner: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.RUNNING)
                    result = self.tasks[focus]
                case TaskStatus_e.WAIT: # Add dependencies of a task to the stack
                    logging.detail("Checking Task Dependencies: %s", focus)
                    match self.incomplete_dependencies(focus):
                        case []:
                            self.queue_entry(focus, status=TaskStatus_e.READY)
                        case [*xs]:
                            logging.detail("Task Blocked: %s on : %s", focus, xs)
                            self.queue_entry(focus)
                            for x in xs:
                                self.queue_entry(x)
                case TaskStatus_e.INIT:
                    logging.detail("Task Initialising: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.WAIT)

                case ArtifactStatus_e.STALE:
                    doot.report.user("Artifact is Stale: %s", focus)
                    logging.detail("Artifact is Stale: %s", focus)
                    for pred in self.network.pred[focus]:
                        self.queue_entry(pred)
                case ArtifactStatus_e.DECLARED if bool(focus):
                    self.queue_entry(focus, status=ArtifactStatus_e.EXISTS)
                case ArtifactStatus_e.DECLARED: # Add dependencies of an artifact to the stack
                    match self.incomplete_dependencies(focus):
                        case [] if not focus.is_concrete():
                            self.queue_entry(focus, status=ArtifactStatus_e.EXISTS)
                        case []:
                            assert(not bool(focus))
                            self.queue_entry(focus)
                            # Returns the artifact, the runner can try to create it, then override the halt
                            result = focus
                        case [*xs]:
                            logging.trace("Artifact Blocked, queuing producer tasks, count: %s", len(xs))
                            self.queue_entry(focus)
                            for x in xs:
                                self.queue_entry(x)
                case TaskStatus_e.DEFINED:
                    logging.detail("Constructing Task Object for concrete spec: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.HALTED)
                case TaskStatus_e.DECLARED:
                    logging.detail("Declared Task dequeued: %s. Instantiating into tracker network.", focus)
                    self.queue_entry(focus)
                case TaskStatus_e.NAMED:
                    doot.report.user("A Name only was queued, it has no backing in the tracker: %s", focus)
                    logging.detail("A Name only was queued, it has no backing in the tracker: %s", focus)

                case x: # Error otherwise
                    raise doot.errors.TrackingError("Unknown task state: ", x)

        else:
            logging.trace("---- Determined Next Task To Be: %s", result)
            # TODO apply task.state.key injections from connected tasks?
            return result
