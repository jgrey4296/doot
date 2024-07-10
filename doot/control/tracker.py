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

# ##-- 3rd party imports
import networkx as nx

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import (FailPolicy_p, Job_i, Task_i, TaskRunner_i,
                            TaskTracker_i)
from doot.control.base_tracker import BaseTracker
from doot.enums import EdgeType_e, ExecutionPolicy_e, TaskStatus_e, TaskMeta_f
from doot.structs import CodeReference, TaskArtifact, TaskName, TaskSpec
from doot.task.base_task import DootTask

# ##-- end 1st party imports

##-- logging
logging    = logmod.getLogger(__name__)
printer    = logmod.getLogger("doot._printer")
track_l    = printer.getChild("track")
fail_l     = printer.getChild("fail")
skip_l     = printer.getChild("skip")
task_l     = printer.getChild("task")
artifact_l = printer.getChild("artifact")
##-- end logging

Node      : TypeAlias      = TaskName|TaskArtifact
Depth     : TypeAlias      = int
PlanEntry : TypeAlias      = tuple[Depth, Node, str]
MAX_LOOP  : Final[int]     = 100

@doot.check_protocol
class DootTracker(BaseTracker, TaskTracker_i):
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


    def _dfs_plan(self) -> list[PlanEntry]:
        """ Generates the Execution plan of queued tasks,
          as a list of the edges it will move through.
          not taking into account priority or status.
        """
        logging.debug("Generating DFS Plan")
        plan  : list[PlanEntry]      = []
        # Reverse the sort because its a stack
        stack : list[PlanEntry]      = [(0, x, "Initial Task") for x in sorted(self.network.pred[self._root_node], key=DootTracker._node_sort, reverse=True)]
        found_count                                = defaultdict(lambda: 0)
        logging.debug("Initial DFS Stack: %s", stack)
        while bool(stack):
            depth, node, desc = stack[-1]
            node_type = "Branch" if bool(self.network.pred[node]) else "Leaf"
            match found_count[node]:
                case 0:
                    found_count[node] += 1
                    plan.append((depth, node, f"{depth}: Enter {node_type} {desc}: {node.readable}"))
                    stack += [(depth+1, x, "Dependency") for x in sorted(self.network.pred[node], key=DootTracker._node_sort, reverse=True)]
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
        logging.debug("Generating BFS Plan")
        plan  : list[PlanEntry]      = []
        queue : list[PlanEntry]      = [(0, x, "Initial Task") for x in sorted(self.network.pred[self._root_node], key=DootTracker._node_sort)]
        found_count                  = defaultdict(lambda: 0)
        logging.debug("Initial BFS Queue: %s", queue)
        while bool(queue):
            depth, node, desc = queue.pop(0)
            node_type = "Branch" if bool(self.network.pred[node]) else "Leaf"
            match found_count[node]:
                case 0:
                    found_count[node] += 1
                    plan.append((depth, node, f"{depth}: Enter {node_type} {desc}: {node.readable}"))
                    queue += [(depth+1, x, "Dependency") for x in sorted(self.network.pred[node], key=DootTracker._node_sort)]
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
        plan                                         = []
        original_tasks    : set[Node]                = set(self.active_set)
        original_statuses : dict[Node, TaskStatus_e] = {x: self.get_status(x) for x in itz.chain(self.specs.keys(), self.artifacts.keys())}

        while bool(self):
            match self.next_for():
                case None:
                    continue
                case Task_i() as spec:
                    logging.info("Plan Next: %s", str(spec.name))
                    plan.append((0, spec.name, str(spec.name)))
                    self.set_status(spec, TaskStatus_e.SUCCESS)
                case TaskArtifact() as art:
                    plan.append((1, art, str(art)))
                    self.set_status(art, TaskStatus_e.EXISTS)
                case x:
                    raise doot.errors.DootTaskTrackingError("Unrecognised reponse while building plan", x)

        self.clear_queue()
        self.tasks = {}
        for x in self.artifacts.keys():
            self.set_status(x, TaskStatus_e.ARTIFACT)
        for x in original_tasks:
            self.queue_entry(x)

        return plan

    def generate_plan(self, *, policy:None|ExecutionPolicy_e=None) -> list[PlanEntry]:
        """ Generate an ordered list of tasks that would be executed.
          Does not expand jobs.
          """
        match policy:
            case None | ExecutionPolicy_e.DEPTH:
                 return self._dfs_plan()
            case ExecutionPolicy_e.BREADTH:
                return self._bfs_plan()
            case ExecutionPolicy_e.PRIORITY:
                return self._priority_plan()
            case _:
                raise doot.errors.DootTaskTrackingError("Unknown plan generation form", policy)



    def write(self, target:pl.Path):
        """ Write the task network out as jsonl  """
        raise NotImplementedError()

    def next_for(self, target:None|str|TaskName=None) -> None|Task_i|TaskArtifact:
        """ ask for the next task that can be performed

          Returns a Task or Artifact that needs to be executed or created
          Returns None if it loops too many times trying to find a target,
          or if theres nothing left in the queue

        """
        if not self.network_is_valid:
            raise doot.errors.DootTaskTrackingError("Network is in an invalid state")

        if target and target not in self.active_set:
            self.queue_entry(target, silent=True)

        focus : None|str|TaskName|TaskArtifact = None
        count = MAX_LOOP
        while bool(self) and 0 < (count:=count-1):
            focus  : TaskName|TaskArtifact = self.deque_entry()
            status : TaskStatus_e          = self.get_status(focus)
            match focus:
                case TaskName():
                    track_l.debug("Tracker Head: %s (Task). State: %s, Priority: %s", focus, self.get_status(focus), self.tasks[focus].priority)
                case TaskArtifact():
                    track_l.debug("Tracker Head: %s (Artifact). State: %s, Priority: %s", focus, self.get_status(focus), self._artifact_status[focus])

            logging.debug("Tracker Active Set Size: %s", len(self.active_set))

            match status:
                case TaskStatus_e.DEAD:
                    track_l.debug("Task is Dead: %s", focus)
                    del self.tasks[focus]
                case TaskStatus_e.DISABLED:
                    track_l.info("Task Disabled: %s", focus)
                case TaskStatus_e.TEARDOWN:
                    track_l.debug("Tearing Down: %s", focus)
                    self.active_set.remove(focus)
                    self.set_status(focus, TaskStatus_e.DEAD)
                case TaskStatus_e.SUCCESS if TaskMeta_f.JOB in focus:
                    track_l.debug("Job Object Success, queuing head: %s", focus)
                    self.queue_entry(focus.root().job_head())
                    if (cleanup:=focus.root().job_head().subtask("cleanup")) in self.specs:
                        self.queue_entry(cleanup)
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                    self.build_network()
                case TaskStatus_e.SUCCESS | TaskStatus_e.EXISTS:
                    track_l.info("Task Succeeded: %s", focus)
                    self.execution_trace.append(focus)
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                    for succ in [x for x in self.network.succ[focus] if self.get_status(x) in TaskStatus_e.success_set]:
                        if nx.has_path(self.network, succ, self._root_node):
                            self.queue_entry(succ)
                case TaskStatus_e.FAILED:  # propagate failure
                    self.active_set.remove(focus)
                    fail_l.warning("Task Failed, Propagating from: %s to: %s", focus, list(self.network.succ[focus]))
                    for succ in self.network.succ[focus]:
                        self.set_status(succ, TaskStatus_e.FAILED)
                case TaskStatus_e.HALTED:  # remove and propagate halted status
                    self.active_set.remove(focus)
                    fail_l.warning("Task Halted, Propagating from: %s to: %s", focus, list(self.network.succ[focus]))
                    for succ in self.network.succ[focus]:
                        self.set_status(succ, TaskStatus_e.HALTED)
                case TaskStatus_e.SKIPPED:
                    skip_l.info("Task was skipped: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.TEARDOWN)
                case TaskStatus_e.RUNNING:
                    track_l.info("Awaiting Runner to update status for: %s", focus)
                    self.queue_entry(focus)
                case TaskStatus_e.READY:   # return the task if its ready
                    track_l.info("Task Ready to run, informing runner: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.RUNNING)
                    return self.tasks[focus]
                case TaskStatus_e.WAIT: # Add dependencies of a task to the stack
                    track_l.info("Checking Task Dependencies: %s", focus)
                    match self.incomplete_dependencies(focus):
                        case []:
                            self.queue_entry(focus, status=TaskStatus_e.READY)
                        case [*xs]:
                            track_l.info("Task Blocked: %s on : %s", focus, xs)
                            self.queue_entry(focus)
                            for x in xs:
                                self.queue_entry(x)
                case TaskStatus_e.INIT:
                    track_l.debug("Task Object Initialising: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.WAIT)

                case TaskStatus_e.STALE:
                    artifact_l.info("Artifact is Stale: %s", focus)
                    for pred in self.network.pred[focus]:
                        self.queue_entry(pred)
                case TaskStatus_e.ARTIFACT if bool(focus):
                    self.queue_entry(focus, status=TaskStatus_e.EXISTS)
                case TaskStatus_e.ARTIFACT: # Add dependencies of an artifact to the stack
                    match self.incomplete_dependencies(focus):
                        case []:
                            assert(not bool(focus))
                            path = focus.expand()
                            fail_l.warning("An Artifact has no incomplete dependencies, yet doesn't exist: %s (expanded: %s)", focus, path)
                            self.queue_entry(focus, status=TaskStatus_e.HALTED)
                            # Returns the artifact, the runner can try to create it, then override the halt
                            return focus
                        case [*xs]:
                            track_l.debug("Artifact Blocked, queuing producer tasks, count: %s", len(xs))
                            self.queue_entry(focus)
                            for x in xs:
                                self.queue_entry(x)
                case TaskStatus_e.DEFINED:
                    track_l.debug("Constructing Task Object for concrete spec: %s", focus)
                    self.queue_entry(focus, status=TaskStatus_e.HALTED)
                case TaskStatus_e.DECLARED:
                    track_l.debug("Declared Task dequeued: %s. Instantiating into tracker network.", focus)
                    self.queue_entry(focus)
                case TaskStatus_e.NAMED:
                    track_l.warning("A Name only was queued, it has no backing in the tracker: %s", focus)

                case x: # Error otherwise
                    raise doot.errors.DootTaskTrackingError("Unknown task state: ", x)

        return None
