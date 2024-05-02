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
        pass

    def bfs_dag(self) -> list[DootTaskName]:
        pass

    def write(self, target:pl.Path):
        # DFS or BFS the dag
        # write out as jsonl
        pass

    def next_for(self, target:None|DootTaskName|str=None) -> None|Job_i|Task_i|DootTaskArtifact:
        """ ask for the next task that can be performed """
        if target and target not in self.active_set:
            self.queue_task(target, silent=True)

        focus : str | DootTaskArtifact | None = None
        while bool(self.task_queue):
            focus : str = self.task_queue.peek()
            logging.debug("Task: %s  State: %s, Priority: %s, Stack: %s", focus, self.task_status(focus), self.network.nodes[focus][PRIORITY], len(self.active_set))

            if focus in self.tasks and self.tasks[focus].priority < self._min_priority:
                logging.warning("Task halted due to reaching minimum priority while tracking: %s", focus)
                self.update_status(focus, TaskStatus_e.HALTED)

            match self.task_status(focus):
                case TaskStatus_e.SUCCESS:
                    self.deque_task()
                    self._reactive_queue(focus)

                case TaskStatus_e.EXISTS: # remove artifact if exists
                    for pred in self.network.pred[focus].keys():
                        logging.debug("Propagating Artifact existence to disable: %s", pred)
                        self.update_status(pred, TaskStatus_e.SUCCESS)
                    self.deque_task()
                    return self.artifacts[focus]

                case TaskStatus_e.HALTED:  # remove and propagate halted status
                    # anything that depends on a halted task in turn gets halted
                    halting = list(self.network.succ[focus].keys())
                    printer.warning("Propagating Halt from: %s to: %s", focus, halting)
                    for pred in halting:
                        self.update_status(pred, TaskStatus_e.HALTED)
                    # And remove the halted task from the active_set
                    self.deque_task()

                case TaskStatus_e.FAILED:  # stop when a task fails, and clear any queued tasks
                    # TODO
                    self.clear_queue()
                    return None

                case TaskStatus_e.RUNNING:
                    raise doot.errors.DootTaskTrackingError("running state shouldn't be possible")

                case TaskStatus_e.READY if focus in self.execution_path: # error on running the same task twice
                    raise doot.errors.DootTaskTrackingError("Task Attempted to run twice: %s", focus)

                case TaskStatus_e.READY:   # return the task if its ready
                    self.execution_path.append(focus)
                    # TODO check this, it might not affect the priority queue
                    self.network.nodes[focus][PRIORITY] -= 1
                    return self.tasks.get(focus, None)

                case TaskStatus_e.ARTIFACT if bool(self.artifacts[focus]): # if an artifact exists, mark it so and remove it
                    logging.info("Artifact Exists: %s", focus)
                    self.update_status(focus, TaskStatus_e.EXISTS)

                case TaskStatus_e.ARTIFACT: # Add dependencies of an artifact to the stack
                    incomplete, all_deps = self._task_dependencies(focus)
                    if bool(incomplete):
                        logging.info("Artifact Blocking Check: %s", focus)
                        self.deque_task()
                        self.insert_task(focus, *incomplete, silent=True)
                    elif bool(all_deps):
                        # Only unblock if something produces thsi artifact
                        logging.debug("Artifact Unblocked: %s", focus)
                        self.update_status(focus, TaskStatus_e.EXISTS)
                    else:
                        self.deque_task()
                        self.insert_task(focus)

                case TaskStatus_e.WAIT | TaskStatus_e.DEFINED: # Add dependencies of a task to the stack
                    incomplete, _ = self._task_dependencies(focus)
                    if bool(incomplete):
                        logging.info("Task Blocked: %s on : %s", focus, incomplete)
                        self.update_status(focus, TaskStatus_e.WAIT)
                        self.deque_task()
                        self.insert_task(focus, *incomplete, silent=True)
                    else:
                        logging.debug("Task Unblocked: %s", focus)
                        self.update_status(focus, TaskStatus_e.READY)

                case TaskStatus_e.DECLARED:
                    logging.warning("Tried to Schedule a Declared but Undefined Task: %s", focus)
                    self.deque_task()
                    if self.network.nodes[focus][PRIORITY] > MIN_PRIORITY:
                        self.insert_task(focus)
                    else:
                        self.update_status(focus, TaskStatus_e.SUCCESS)

                case x: # Error otherwise
                    raise doot.errors.DootTaskTrackingError("Unknown task state: ", x)

        return None
