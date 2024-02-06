#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

# import abc
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
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

printer = logmod.getLogger("doot._printer")

import networkx as nx
import boltons.queueutils
from collections import defaultdict
import tomlguard
import doot
import doot.errors
import doot.constants as const
from doot.enums import TaskStateEnum
from doot._abstract import Job_i, Task_i, FailPolicy_p
from doot.structs import DootTaskArtifact, DootTaskSpec, DootTaskName, DootCodeReference
from doot._abstract import TaskTracker_i, TaskRunner_i, TaskBase_i
from doot.task.base_task import DootTask

ROOT             : Final[str]                  = "__root" # Root node of dependency graph
STATE            : Final[str]                  = "state"  # Node attribute name
PRIORITY         : Final[str]                  = "priority"
COMPLETE_STATES  : Final[set[TaskStateEnum]]   = {TaskStateEnum.SUCCESS, TaskStateEnum.EXISTS}
DECLARE_PRIORITY : Final[int]                  = 10
MIN_PRIORITY     : Final[int]                  = -10

class EDGE_E(enum.Enum):
    TASK               = enum.auto()
    ARTIFACT           = enum.auto()
    TASK_CROSS         = enum.auto() # Task to artifact
    ARTIFACT_CROSS     = enum.auto() # artifact to task

class BaseTracker(TaskTracker_i):
    """ An example tracker implementation to extend """

    state_e            = TaskStateEnum
    INITIAL_TASK_STATE = TaskStateEnum.DEFINED

    def __init__(self, shadowing:bool=False, *, policy=None):
        self.policy                                                              = policy
        self.tasks                   : dict[str, TaskBase_i]                     = {}
        self.artifacts               : dict[str, DootTaskArtifact]               = {}
        self.task_graph              : nx.DiGraph                                = nx.DiGraph()
        self.active_set              : list[str|DootTaskName|DootTaskArtifact]   = set()
        self.execution_path          : list[str]                                 = []
        self.shadowing               : bool                                      = shadowing
        self._root_name              : str                                       = ROOT
        self._build_late             : list[str]                                 = list()
        self.task_queue                                                          = boltons.queueutils.HeapPriorityQueue()
        self._declare_priority                                                   = DECLARE_PRIORITY
        self._min_priority                                                       = MIN_PRIORITY

        self.task_graph.add_node(ROOT, state=self.state_e.WAIT)

    def __bool__(self):
        return bool(self.active_set)

    def __len__(self):
        return len(self.tasks)

    def __iter__(self) -> Generator[Any,Any,Any]:
        while bool(self):
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
                self.task_graph.add_node(str(artifact), state=self.state_e.ARTIFACT, priority=self._declare_priority)
                # connect to indefinites
                for x in filter(lambda x: (not x.is_definite) and artifact in x, self.artifacts.values()):
                    self.task_graph.add_edge(str(artifact), str(x), type=EDGE_E.ARTIFACT)
            case DootTaskArtifact():
                self.artifacts[str(artifact)] = artifact
                self.task_graph.add_node(str(artifact), state=self.state_e.ARTIFACT, priority=self._declare_priority)
                # connect to definites
                for x in filter(lambda x: x.is_definite and x in artifact, self.artifacts.values()):
                    self.task_graph.add_edge(str(x), str(artifact), type=EDGE_E.ARTIFACT)

        return str(artifact)

    def _prep_task(self, spec:DootTaskSpec|TaskBase_i) -> TaskBase_i:
        """ Internal utility method to convert task identifier into actual task """
        # Build the Task if necessary
        match spec:
            case DootTaskSpec(ctor=DootTaskName() as ctor) if str(ctor) in self.tasks:
                # specialize a loaded task
                base_spec          = self.tasks.get(str(ctor)).spec
                inital_specialized = base_spec.specialize_from(spec)
                cli_specialized    = self._insert_cli_args_into_spec(initial_specialized)
                if cli_specialized.ctor is None:
                    raise doot.errors.DootTaskTrackingError("Attempt to specialize task failed: %s", spec.name)

                task = cli_specialized.build()
            case DootTaskSpec(ctor=DootCodeReference() as ctor) if spec.check(ensure=TaskBase_i):
                cli_specialized    = self._insert_cli_args_into_spec(spec)
                task : TaskBase_i = cli_specialized.build()
            case DootTaskSpec():
                cli_specialized    = self._insert_cli_args_into_spec(spec)
                task : TaskBase_i = DootTask(cli_specialized)
            case TaskBase_i():
                task = spec
            case _:
                raise doot.errors.DootTaskTrackingError("Unknown task attempted to be added: %s", spec)

        # Check it doesn't shadow another task
        match task.name in self.tasks, task.name in self.task_graph: # type: ignore
            case True, False:
                raise doot.errors.DootTaskTrackingError("Task exists in defined tasks, but not the task graph")
            case True, True if not self.shadowing:
                raise doot.errors.DootTaskTrackingError("Task with Duplicate Name not added: ", task.name)
            case True, True:
                logging.warning("Task Shadowed by Duplicate Name: %s", task.name)
            case False, True:
                logging.debug("Defining a declared dependency task: %s", task.name)

        return task

    def _insert_cli_args_into_spec(self, spec:DootTaskSpec):
        if spec.name not in doot.args.on_fail({}).tasks():
            return spec

        spec_extra : dict = dict(spec.extra.items())
        for key,val in doot.args.tasks[str(spec.name)].items():
            spec_extra[key] = val

        spec.extra = tomlguard.TomlGuard(spec_extra)
        return spec

    def _insert_dependencies(self, task):
        for pre in task.depends_on:
            logging.debug("Connecting Dependency: %s -> %s", pre, task.name)
            match pre:
                case {"task": taskname}:
                    raise TypeError("Task Deps should not longer be dicts")
                case pl.Path():
                    pre = self._prep_artifact(DootTaskArtifact(pre))
                    self.task_graph.add_edge(pre, task.name, type=EDGE_E.ARTIFACT_CROSS)
                case DootTaskArtifact():
                    pre = self._prep_artifact(pre)
                    self.task_graph.add_edge(pre, task.name, type=EDGE_E.ARTIFACT_CROSS)
                case DootTaskName() if all([(in_graph:=str(pre) in self.task_graph),(has_args:=bool(pre.args))]):
                    base_spec                 = self.tasks[str(pre)].spec
                    name_spec                 = DootTaskSpec.from_name(pre)
                    name_spec.ctor            = base_spec.name
                    name_spec.required_for.append(task.name)
                    self.add_task(name_spec)
                case DootTaskName() if in_graph and not has_args:
                    # just connect if the tracker already knows the task
                    self.task_graph.add_edge(str(pre), task.name, type=EDGE_E.TASK)
                case DootTaskName() if has_args:
                    assert(str(pre) not in self.task_graph.nodes)
                    name_spec      = DootTaskSpec.from_name(pre.specialize(info="late"))
                    name_spec.ctor = pre
                    name_spec.required_for.append(task.name)
                    self._build_late.append(name_spec)
                case str() | DootTaskName():
                    # Otherwise add a dummy task until its defined
                    self.task_graph.add_node(str(pre), state=self.state_e.DECLARED, priority=self._declare_priority)
                    self.task_graph.add_edge(str(pre), task.name, type=EDGE_E.TASK)
                case _:
                    raise doot.errors.DootTaskTrackingError("Unknown dependency task attempted to be added: %s", pre)

    def _insert_dependents(self, task):
        for post in task.required_for:
            logging.debug("Connecting Successor: %s -> %s", task.name, post)
            match post:
                case {"task": taskname}:
                    raise TypeError("Task Deps should not longer be dicts")
                case pl.Path():
                    post = self._prep_artifact(DootTaskArtifact(post))
                    self.task_graph.add_edge(task.name, post, type=EDGE_E.TASK_CROSS)
                case DootTaskArtifact():
                    post = self._prep_artifact(post)
                    self.task_graph.add_edge(task.name, post, type=EDGE_E.TASK_CROSS)

                case DootTaskName() if all([(in_graph:=str(post) in self.task_graph), (has_args:=bool(post.args))]):
                    base_spec                 = self.tasks[str(post)].spec
                    name_spec                 = DootTaskSpec.from_name(post)
                    name_spec.ctor            = base_spec.name
                    name_spec.depends_on.append(task.name)
                    self.add_task(name_spec)
                case DootTaskName() if in_graph and not has_args:
                    # just connect if the tracker already knows the task
                    self.task_graph.add_edge(task.name, str(post), type=EDGE_E.TASK)
                case DootTaskName() if has_args:
                    assert(str(post) not in self.task_graph.nodes)
                    name_spec      = DootTaskSpec.from_name(post.specialize(info="late"))
                    name_spec.ctor = post
                    name_spec.depends_on.append(task.name)
                    self._build_late.append(name_spec)
                case str() | DootTaskName():
                    # Otherwise add a dummy task until its defined
                    self.task_graph.add_node(str(post), state=self.state_e.DECLARED, priority=self._declare_priority)
                    self.task_graph.add_edge(task.name, str(post), type=EDGE_E.TASK)
                case _:
                    raise doot.errors.DootTaskTrackingError("Unknown successor task attempted to be added: %s", post)

    def _insert_according_to_queue_behaviour(self, task):
        match task.spec.queue_behaviour:
            case "auto":
                self.queue_task(task.name)
            case "reactive":
                self.task_graph.nodes[task.name][REACTIVE_ADD] = True
            case "default":
                pass
            case _:
                raise doot.errors.DootTaskTrackingError("Unknown queue behaviour specified: %s", task.spec.queue_behaviour)

    def _task_dependencies(self, task) -> tuple[list[str], list[str]]:
        # TODO detect 'read' actions as implicit dependencies
        dependencies = list(self.task_graph.pred[task].keys())
        incomplete   = list(filter(lambda x: self.task_state(x) not in COMPLETE_STATES, dependencies))
        return incomplete, dependencies

    def _task_products(self, task) -> tuple[list[str], list[str]]:
        """
          Get task 'required-for' files: [not-existing, total]
        """
        # TODO detect 'write!' actions as implicit products
        looking_for  = [EDGE_E.ARTIFACT, EDGE_E.TASK_CROSS]
        artifacts    = list(map(lambda x: x[0], filter(lambda x: x[1].get('type', None) in looking_for, self.task_graph.succ[str(task)].items())))
        incomplete   = list(filter(lambda x: not bool(self.artifacts[x]), artifacts))

        return incomplete, artifacts

    def _task_dependents(self, task) -> tuple[list[str], list[str]]:
        raise NotImplementedError()

    def queue_task(self, *tasks:str|DootTaskName|DootTaskArtifact|tuple, silent=False) -> None:
        """
          Add tasks to the queue.
          By default it does *not* complain on trying to re-add already queued tasks,
        """
        # TODO queue the task's setup task if it exists / hasn't been executed already
        # TODO if only task name is specified, without group, and theres no ambiguity, accept that
        logging.debug("Queue Request: %s", tasks)
        targets = set()
        for task in tasks:
            # Retrieve the actual task
            match task:
                case str() | DootTaskName() | DootTaskArtifact() if str(task) in self.active_set:
                    if not silent:
                        logging.warning("Trying to queue an already active task: %s", task)
                    continue
                case str() | DootTaskName() | DootTaskArtifact() if str(task) not in self.task_graph.nodes:
                    raise doot.errors.DootTaskTrackingError("Attempted To Queue an undefined Task: %s", task)
                case DootTaskArtifact():
                    targets.add(task)
                case str() | DootTaskName():
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
                self.task_queue.add(str(task), self.task_graph.nodes[str(task)].get(PRIORITY, self._declare_priority))

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
        logging.debug("Building %s abstract tasks", len(self._build_late))
        while bool(self._build_late):
            curr = self._build_late.pop()
            assert(isinstance(curr, DootTaskSpec))
            self.add_task(curr)

        return all([nx.is_directed_acyclic_graph(self.task_graph),
                    self.declared_set() == self.defined_set()
                   ])

    def declared_set(self) -> set[str]:
        """ Get the set of tasks which have been declared, directly or indirectly """
        return set(self.task_graph.nodes)

    def defined_set(self) -> set[str]:
        """ get the set of tasks which are explicitly defined """
        return set(self.tasks.keys())

    def task_state(self, task:str|DootTaskName|DootTaskArtifact|pl.Path) -> self.state_e:
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
