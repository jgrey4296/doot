#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

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
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator, Literal)
# from uuid import UUID, uuid1
# from weakref import ref

# from bs4 import BeautifulSoup
import boltons.queueutils
import networkx as nx
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging
printer = logmod.getLogger("doot._printer")

from collections import defaultdict
import doot
import doot.errors
import doot.constants as const
from doot.enums import TaskStateEnum
from doot._abstract import Tasker_i, Task_i, FailPolicy_p
from doot.structs import DootTaskArtifact, DootTaskSpec, DootStructuredName
from doot._abstract import TaskTracker_i, TaskRunner_i, TaskBase_i
from doot.task.base_task import DootTask

ROOT             : Final[str]                  = "__root" # Root node of dependency graph
STATE            : Final[str]                  = "state"  # Node attribute name
PRIORITY         : Final[str]                  = "priority"
DECLARE_PRIORITY : Final[int]                  = 10
MIN_PRIORITY     : Final[int]                  = -10
complete_states  : Final[set[TaskStateEnum]]   = {TaskStateEnum.SUCCESS, TaskStateEnum.EXISTS}

class _TrackerEdgeType(enum.Enum):
    TASK               = enum.auto()
    ARTIFACT           = enum.auto()
    TASK_CROSS         = enum.auto() # Task to artifact
    ARTIFACT_CROSS     = enum.auto() # artifact to task

@doot.check_protocol
class DootTracker(TaskTracker_i):
    """
    track dependencies in a networkx digraph,
    predecessors of a node are its dependencies.
      ie: SubDependency -> Dependency -> Task -> ROOT

    tracks definite and indefinite artifacts as products and dependencies of tasks as well.

    the `task_graph` stores nodes as full names of tasks
    """
    state_e            = TaskStateEnum
    INITIAL_TASK_STATE = TaskStateEnum.DEFINED

    def __init__(self, shadowing:bool=False, *, policy=None):
        super().__init__(policy=policy) # self.tasks
        self.artifacts              : dict[str, DootTaskArtifact]                       = {}
        self.task_graph              : nx.DiGraph                                        = nx.DiGraph()
        self.active_set             : list[str|DootStructuredName|DootTaskArtifact]     = set()
        self.task_queue                                                                 = boltons.queueutils.HeapPriorityQueue()
        self.execution_path         : list[str]                                         = []
        self.shadowing              : bool                                              = shadowing
        self._root_name             : str = ROOT

        self.task_graph.add_node(ROOT, state=self.state_e.WAIT)

    def __len__(self):
        return len(self.tasks)

    def __iter__(self) -> Generator[Any,Any,Any]:
        while bool(self.active_set):
            logging.info("Tracker Queue: %s", self.active_set)
            yield self.next_for()

    def __contains__(self, target:str) -> bool:
        # TODO handle definite artifacts -> indefinite artifacts
        return target in self.tasks

    def _prep_artifact(self, artifact:DootTaskArtifact) -> str:
        """ convert a path to an artifact, and connect it with matching artifacts """
        match artifact:
            case _ if str(artifact) in self.artifacts:
                pass
            case DootTaskArtifact() if artifact.is_definite:
                self.artifacts[str(artifact)] = artifact
                self.task_graph.add_node(str(artifact), state=self.state_e.ARTIFACT, priority=DECLARE_PRIORITY)
                # connect to indefinites
                for x in filter(lambda x: (not x.is_definite) and artifact in x, self.artifacts.values()):
                    self.task_graph.add_edge(str(artifact), str(x), type=_TrackerEdgeType.ARTIFACT)
            case DootTaskArtifact():
                self.artifacts[str(artifact)] = artifact
                self.task_graph.add_node(str(artifact), state=self.state_e.ARTIFACT, priority=DECLARE_PRIORITY)
                # connect to definites
                for x in filter(lambda x: x.is_definite and x in artifact, self.artifacts.values()):
                    self.task_graph.add_edge(str(x), str(artifact), type=_TrackerEdgeType.ARTIFACT)

        return str(artifact)

    def _prep_task(self, task:DootTaskSpec|TaskBase_i) -> TaskBase_i:
        """ Internal utility method to convert task identifier into actual task """
        # Build the Task if necessary
        match task:
            case DootTaskSpec(ctor=ctor) if isinstance(ctor, type) and issubclass(ctor, TaskBase_i):
                task : TaskBase_i = task.ctor(task)
            case DootTaskSpec(ctor=None, ctor_name=ctor_name) if str(ctor_name) in self.tasks:
                # specialize a loaded task
                base_spec   = self.tasks.get(str(ctor_name)).spec
                specialized = base_spec.specialize_from(task)
                if specialized.ctor is None:
                    raise doot.errors.DootTaskTrackingError("Attempt to specialize task failed: %s", task.name)

                task = specialized.ctor(task)
                return task
            case DootTaskSpec():
                task : TaskBase_i = DootTask(task)
            case TaskBase_i():
                pass
            case _:
                raise doot.errors.DootTaskTrackingError("Unknown task attempted to be added: %s", task)

        # Check it doesn't shadow another task
        match task.name in self.tasks, task.name in self.task_graph: # type: ignore
            case True, False:
                raise doot.errors.DootConfigError("Task exists in defined tasks, but not the task graph")
            case True, True if not self.shadowing:
                raise doot.errors.DootTaskTrackingError("Task with Duplicate Name not added: ", task.name)
            case True, True:
                logging.warning("Task Shadowed by Duplicate Name: %s", task.name)
            case False, True:
                logging.debug("Defining a declared dependency task: %s", task.name)

        return task

    def _task_dependencies(self, task) -> tuple[list[str], list[str]]:
        # TODO detect 'read' actions as implicit dependencies
        dependencies = list(self.task_graph.pred[task].keys())
        incomplete   = list(filter(lambda x: self.task_state(x) not in complete_states, dependencies))
        return incomplete, dependencies

    def _task_products(self, task) -> tuple[list[str], list[str]]:
        """
          Get task 'required-for' files: [not-existing, total]
        """
        # TODO detect 'write!' actions as implicit products
        looking_for  = [_TrackerEdgeType.ARTIFACT, _TrackerEdgeType.TASK_CROSS]
        artifacts    = list(map(lambda x: x[0], filter(lambda x: x[1].get('type', None) in looking_for, self.task_graph.succ[str(task)].items())))
        incomplete   = list(filter(lambda x: not bool(self.artifacts[x]), artifacts))

        return incomplete, artifacts

    def add_task(self, task:DootTaskSpec|TaskBase_i, *, no_root_connection=False) -> None:
        """ add a task description into the tracker, but don't queue it
        connecting it with its dependencies and tasks that depend on it
        """
        task = self._prep_task(task)
        assert(isinstance(task, TaskBase_i))

        # Store it
        self.tasks[task.name] = task

        # Insert into dependency graph
        self.task_graph.add_node(task.name, state=self.INITIAL_TASK_STATE, priority=task.spec.priority)

        # Then connect it to the rest of the graph
        if not no_root_connection and task.name:
            self.task_graph.add_edge(task.name, ROOT)

        for pre in task.depends_on:
            logging.debug("Connecting Dependency: %s -> %s", pre, task.name)
            match pre:
                case pl.Path():
                    pre = self._prep_artifact(DootTaskArtifact(pre))
                    self.task_graph.add_edge(pre, task.name, type=_TrackerEdgeType.ARTIFACT_CROSS)
                case DootTaskArtifact():
                    pre = self._prep_artifact(pre)
                    self.task_graph.add_edge(pre, task.name, type=_TrackerEdgeType.ARTIFACT_CROSS)
                case DootStructuredName() if str(pre) in self.task_graph:
                    # just connect if the tracker already knows the tas
                    self.task_graph.add_edge(str(pre), task.name, type=_TrackerEdgeType.TASK)
                case str() | DootStructuredName():
                    # Otherwise add a dummy task until its defined
                    self.task_graph.add_node(str(pre), state=self.state_e.DECLARED, priority=DECLARE_PRIORITY)
                    self.task_graph.add_edge(str(pre), task.name, type=_TrackerEdgeType.TASK)
                case _:
                    raise doot.errors.DootTaskTrackingError("Unknown dependency task attempted to be added: %s", pre)

        for post in task.required_for:
            logging.debug("Connecting Successor: %s -> %s", task.name, post)
            match post:
                case pl.Path():
                    post = self._prep_artifact(DootTaskArtifact(post))
                    self.task_graph.add_edge(task.name, post, type=_TrackerEdgeType.TASK_CROSS)
                case DootTaskArtifact():
                    post = self._prep_artifact(post)
                    self.task_graph.add_edge(task.name, post, type=_TrackerEdgeType.TASK_CROSS)
                case str() | DootStructuredName() if str(post) in self.task_graph:
                    # Again, if the task is known, use it
                    self.task_graph.add_edge(task.name, str(post), type=_TrackerEdgeType.TASK)
                case str() | DootStructuredName():
                    # Or create a dummy task
                    self.task_graph.add_node(str(post), state=self.state_e.DECLARED, priority=DECLARE_PRIORITY)
                    self.task_graph.add_edge(task.name, str(post), type=_TrackerEdgeType.TASK)
                case _:
                    raise doot.errors.DootTaskTrackingError("Unknown successor task attempted to be added: %s", post)

    def queue_task(self, *tasks:str|DootStructuredName|DootTaskArtifact|tuple, silent=False) -> None:
        """
          Add tasks to the queue.
          By default it does *not* complain on trying to re-add already queued tasks,
        """
        # TODO queue the task's setup task if it exists / hasn't been executed already
        logging.debug("Queue Request: %s", tasks)
        targets = set()
        for task in tasks:
            # Retrieve the actual task
            match task:
                case str() | DootStructuredName() | DootTaskArtifact() if str(task) in self.active_set:
                    if not silent:
                        logging.warning("Trying to queue an already active task: %s", task)
                    continue
                case str() | DootStructuredName() | DootTaskArtifact() if str(task) not in self.task_graph.nodes:
                    raise doot.errors.DootTaskTrackingError("Attempted To Queue an undefined Task: %s", task)
                case DootTaskArtifact():
                    targets.add(task)
                case str() | DootStructuredName():
                    # Queue successor artifacts instead of the task itself
                    incomplete, total = self._task_products(task)
                    if bool(incomplete) or not bool(total):
                        targets.add(task)
                    else:
                        targets.update(total)
                case _:
                    raise doot.errors.DootTaskTrackingError("Unrecognized Queue Argument: %s", task)


        logging.debug("Queueing: %s", targets)
        for task in targets:
            if str(task) not in self.active_set:
                self.active_set.add(str(task))
                self.task_queue.add(str(task), self.task_graph.nodes[str(task)].get(PRIORITY, DECLARE_PRIORITY))

    def deque_task(self) -> None:
        focus = self.task_queue.pop()
        self.task_graph.nodes[focus][PRIORITY] -= 1
        logging.debug("Task Priority Decrement: %s = %s", focus, self.task_graph.nodes[focus][PRIORITY])
        self.active_set.remove(focus)

    def clear_queue(self) -> None:
        # TODO queue the task's failure/cleanup task
        self.active_set =  set()
        self.task_queue = boltons.queueutils.HeapPriorityQueue()

    def validate(self) -> bool:
        """
        run tests to check the dependency graph is acceptable
        """
        return all([nx.is_directed_acyclic_graph(self.task_graph),
                    self.declared_set() == self.defined_set()
                   ])

    def declared_set(self) -> set[str]:
        """ Get the set of tasks which have been declared, directly or indirectly """
        return set(self.task_graph.nodes)

    def defined_set(self) -> set[str]:
        """ get the set of tasks which are explicitly defined """
        return set(self.tasks.keys())

    def update_state(self, task:str|TaskBase_i|DootTaskArtifact, state:self.state_e):
        """ update the state of a task in the dependency graph """
        logging.debug("Updating State: %s -> %s", task, state)
        match task, state:
            case str(), self.state_e() if task in self.task_graph:
                self.task_graph.nodes[task][STATE] = state
            case TaskBase_i(), self.state_e() if task.name in self.task_graph:
                self.task_graph.nodes[task.name][STATE] = state
            case DootTaskArtifact(), self.state_e() if task in self.task_graph:
                self.task_graph.nodes[task][STATE] = state
            case _, _:
                raise doot.errors.DootTaskTrackingError("Bad task update state args", task, state)

    def task_state(self, task:str|DootStructuredName|pl.Path) -> self.state_e:
        """ Get the state of a task """
        if str(task) in self.task_graph.nodes:
            return self.task_graph.nodes[str(task)][STATE]
        else:
            raise doot.errors.DootTaskTrackingError("Unknown Task state requested: %s", task)

    def all_states(self) -> dict:
        """ Get a dict of all tasks, and their current state """
        nodes = self.task_graph.nodes
        return {x: y[STATE] for x,y in nodes.items()}

    def write(self, target:pl.Path) -> None:
        """ Write the dependency graph to a file """
        raise NotImplementedError()

    def read(self, target:pl.Path) -> None:
        """ Read the dependency graph from a file """
        raise NotImplementedError()

    def next_for(self, target:None|str=None) -> None|Tasker_i|Task_i|DootTaskArtifact:
        """ ask for the next task that can be performed """
        if target and target not in self.active_set:
            self.queue_task(target, silent=True)

        focus : str | DootTaskArtifact | None = None
        while bool(self.task_queue):
            focus : str = self.task_queue.peek()
            logging.debug("Task: %s  State: %s, Priority: %s, Stack: %s", focus, self.task_state(focus), self.task_graph.nodes[focus][PRIORITY], self.active_set)

            if focus in self.task_graph and self.task_graph.nodes[focus][PRIORITY] < MIN_PRIORITY:
                logging.warning("Task halted due to reaching minimum priority while tracking: %s", focus)
                self.update_state(focus, self.state_e.HALTED)

            match self.task_state(focus):
                case self.state_e.SUCCESS:
                    self.deque_task()
                case self.state_e.EXISTS: # remove task on completion
                    for pred in self.task_graph.pred[focus].keys():
                        logging.debug("Propagating Artifact existence to disable: %s", pred)
                        self.update_state(pred, self.state_e.SUCCESS)
                    self.deque_task()
                    return self.artifacts[focus]
                case self.state_e.HALTED:  # remove and propagate halted status
                    # anything that depends on a halted task in turn gets halted
                    halting = list(self.task_graph.succ[focus].keys())
                    printer.warning("Propagating Halt from: %s to:", focus, halting)
                    for pred in halting:
                        self.update_state(pred, self.state_e.HALTED)
                    # And remove the halted task from the active_set
                    self.deque_task()
                case self.state_e.FAILED:  # stop when a task fails, and clear any queued tasks
                    self.clear_queue()
                    return None
                case self.state_e.READY if focus in self.execution_path: # error on running the same task twice
                    raise doot.errors.DootTaskTrackingError("Task Attempted to run twice: %s", focus)
                case self.state_e.READY:   # return the task if its ready
                    self.execution_path.append(focus)
                    return self.tasks.get(focus, None)
                case self.state_e.ARTIFACT if bool(self.artifacts[focus]): # if an artifact exists, mark it so and remove it
                    logging.info("Artifact Exists: %s", focus)
                    self.update_state(focus, self.state_e.EXISTS)
                case self.state_e.ARTIFACT: # Add dependencies of an artifact to the stack
                    incomplete, all_deps = self._task_dependencies(focus)
                    if bool(incomplete):
                        logging.info("Artifact Blocking Check: %s", focus)
                        self.deque_task()
                        self.queue_task(focus, *incomplete, silent=True)
                    elif bool(all_deps):
                        logging.debug("Artifact Unblocked: %s", focus)
                        self.update_state(focus, self.state_e.EXISTS)
                    else:
                        self.deque_task()
                        self.queue_task(focus)

                case self.state_e.WAIT | self.state_e.DEFINED: # Add dependencies of a task to the stack
                    incomplete, _ = self._task_dependencies(focus)
                    if bool(incomplete):
                        logging.info("Task Blocked: %s on : %s", focus, incomplete)
                        self.update_state(focus, self.state_e.WAIT)
                        self.deque_task()
                        self.queue_task(focus, *incomplete, silent=True)
                    else:
                        logging.debug("Task Unblocked: %s", focus)
                        self.update_state(focus, self.state_e.READY)

                case self.state_e.DECLARED: # warn on undefined tasks
                    logging.warning("Tried to Schedule a Declared but Undefined Task: %s", focus)
                    self.deque_task()
                    self.update_state(focus, self.state_e.SUCCESS)
                case x: # Error otherwise
                    raise doot.errors.DootTaskTrackingError("Unknown task state: ", x)

        return None
