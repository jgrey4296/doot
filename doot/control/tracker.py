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
# import boltons
# import construct as C
# import dirty-equals as deq
# import graphviz
# import matplotlib.pyplot as plt
# import more_itertools as itzplus
import networkx as nx
# import numpy as np
# import pandas
# import pomegranate as pom
# import pony import orm
# import pronouncing
# import pyparsing as pp
# import rich
# import seaborn as sns
# import sklearn
# import stackprinter # stackprinter.set_excepthook(style='darkbg2')
# import sty
# import sympy
# import tomllib
# import toolz
# import tqdm
# import validators
# import z3
# import spacy # nlp = spacy.load("en_core_web_sm")

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from collections import defaultdict
import doot
import doot.errors
from doot.enums import TaskStateEnum
from doot._abstract import Tasker_i, Task_i, FailPolicy_p
from doot.structs import DootTaskArtifact, DootTaskSpec, DootStructuredName
from doot._abstract import TaskTracker_i, TaskRunner_i, TaskBase_i

ROOT  : Final[str] = "__root" # Root node of dependency graph
STATE : Final[str] = "state"  # Node attribute name

class _TrackerEdgeType(enum.Enum):
    TASK     = enum.auto()
    ARTIFACT = enum.auto()


@doot.check_protocol
class DootTracker(TaskTracker_i):
    """
    track dependencies in a networkx digraph,
    successors of a node are its dependencies.
      ie: ROOT -> Task -> Dependency -> SubDependency

    tracks definite and indefinite artifacts as products and dependencies of tasks as well.
    """

    def __init__(self, shadowing:bool=False, *, policy=None):
        super().__init__(policy=policy) # self.tasks
        self.artifacts            : dict[str, DootTaskArtifact]                       = {}
        self.indefinite_artifacts : dict[str, DootTaskArtifact]                       = {}
        self.dep_graph            : nx.DiGraph                                        = nx.DiGraph()
        self.task_stack           : list[str|DootStructuredName|DootTaskArtifact]    = []
        self.execution_path       : list[str]                                         = []
        self.shadowing            : bool                                              = shadowing

        self.dep_graph.add_node(ROOT, state=self.state_e.WAIT)

    def __iter__(self) -> Generator[Any,Any,Any]:
        while bool(self.task_stack):
            yield self.next_for()

    def __contains__(self, target:str) -> bool:
        # TODO handle definite artifacts -> indefinite artifacts
        return target in self.tasks

    def _add_artifact(self, path:pl.Path) -> DootTaskArtifact:
        """ convert a path to an artifact, and connect it with matching artifacts """
        artifact = DootTaskArtifact(path)
        match artifact:
            case _ if artifact in self.dep_graph:
                pass
            case DootTaskArtifact() if artifact.is_definite:
                self.artifacts[str(artifact)] = artifact
                self.dep_graph.add_node(artifact, state=self.state_e.ARTIFACT)
                for x in self.indefinite_artifacts.values(): # connect definite to indefinites
                    if artifact.matches(x):
                        self.dep_graph.add_edge(x, artifact, type=_TrackerEdgeType.ARTIFACT)
            case DootTaskArtifact():
                self.indefinite_artifacts[str(artifact)] = artifact
                self.dep_graph.add_node(artifact, state=self.state_e.ARTIFACT)
                for x in self.artifacts.values(): # connect indefinite to definites
                    if x.matches(artifact):
                        self.dep_graph.add_edge(artifact, x, type=_TrackerEdgeType.ARTIFACT)

        return artifact

    def add_task(self, task:DootTaskSpec|TaskBase_i, *, no_root_connection=False) -> None:
        """ add a task description into the tracker, but don't queue it
        connecting it with its dependencies and tasks that depend on it
        """
        # Build the Task if necessary
        if isinstance(task, DootTaskSpec):
            task : TaskBase_i = task.ctor(task)

        match task.name in self.tasks, self.shadowing, self.tasks.get(task.name): # type: ignore
            case True, _, False:
                pass
            case True, False, _:
                raise doot.errors.DootTaskTrackingError("Task with Duplicate Name not added: ", task.name)
            case True, True, _:
                logging.warning("Task Shadowed by Duplicate Name: %s", task.name)

        self.tasks[task.name] = task
        task_state = self.state_e.READY if not bool(task.runs_after) else self.state_e.DEFINED
        self.dep_graph.add_node(task.name, state=task_state)
        if not no_root_connection:
            self.dep_graph.add_edge(ROOT, task.name)

        for pre in task.runs_after:
            edge_type = _TrackerEdgeType.TASK
            match pre:
                case str() if pre not in self.dep_graph:
                    self.dep_graph.add_node(pre, state=self.state_e.DECLARED)
                case pl.Path():
                    pre = self._add_artifact(pre)
                    edge_type = _TrackerEdgeType.ARTIFACT

            self.dep_graph.add_edge(task.name, pre, type=edge_type)

        for post in task.runs_before:
            edge_type = _TrackerEdgeType.TASK
            match post:
                case str() if post not in self.dep_graph:
                    self.dep_graph.add_node(post, state=self.state_e.DECLARED)
                case pl.Path():
                    post      = self._add_artifact(post)
                    edge_type = _TrackerEdgeType.ARTIFACT

            self.dep_graph.add_edge(post, task.name, type=edge_type)

    def queue_task(self, task:str|DootStructuredName) -> None:
        if task not in self.tasks:
            raise doot.errors.DootTaskTrackingError("Can't queue a task that isn't loaded in the tracker", task)
        self.task_stack.append(task)

    def next_for(self, target:None|str=None) -> None|Tasker_i|Task_i:
        """ ask for the next task that can be performed """
        if target and target not in self.task_stack:
            self.task_stack.append(target)

        complete_states                       = {self.state_e.SUCCESS, self.state_e.EXISTS}
        focus : str | DootTaskArtifact | None = None
        adj                                   = dict(self.dep_graph.adjacency())
        while bool(self.task_stack):
            focus        = self.task_stack[-1]
            logging.debug("Task: %s  State: %s, Stack: %s", focus, self.task_state(focus), self.task_stack)
            match self.task_state(focus):
                case self.state_e.SUCCESS: # remove task on completion
                    self.task_stack.pop()
                case self.state_e.EXISTS:  # remove artifact when it exists
                    self.task_stack.pop()
                case self.state_e.HALTED:  # remove and propagate halted status
                    # anything that depends on a halted task in turn gets halted
                    for pred in self.dep_graph.pred[focus].keys():
                        self.update_state(pred, self.state_e.HALTED)
                    # And remove the halted task from the task_stack
                    self.task_stack.pop()
                case self.state_e.FAILED:  # stop when a task fails, and clear any queued tasks
                    self.task_stack = []
                    return None
                case self.state_e.READY if focus in self.execution_path: # error on running the same task twice
                    raise doot.errors.DootTaskTrackingError("Task Attempted to run twice: %s", focus)
                case self.state_e.READY:   # return the task if its ready
                    self.execution_path.append(focus)
                    return self.tasks.get(focus, None)
                case self.state_e.ARTIFACT if bool(focus): # if an artifact exists, mark it so
                    self.update_state(focus, self.state_e.EXISTS)
                case self.state_e.ARTIFACT: # Add dependencies of an artifact to the stack
                    dependencies = list(adj[focus].keys())
                    incomplete   = list(filter(lambda x: self.task_state(x) not in complete_states, dependencies))
                    if bool(incomplete):
                        self.task_stack += incomplete
                    else:
                        self.update_state(focus, self.state_e.EXISTS)
                case self.state_e.WAIT | self.state_e.DEFINED: # Add dependencies of a task to the stack
                    dependencies = list(adj[focus].keys())
                    incomplete   = list(filter(lambda x: self.task_state(x) not in complete_states, dependencies))
                    if bool(incomplete):
                        self.task_stack += incomplete
                    else:
                        self.update_state(focus, self.state_e.READY)
                case self.state_e.DECLARED: # warn on undefined tasks
                    logging.warning("Tried to Schedule a Declared but Undefined Task: %s", focus)
                    self.task_stack.pop()
                    self.update_state(focus, self.state_e.SUCCESS)
                case _: # Error otherwise
                    raise doot.errors.DootTaskTrackingError("Unknown task state: ", x)

        return None

    def validate(self) -> bool:
        """
        run tests to check the dependency graph is acceptable
        """
        return all([nx.is_directed_acyclic_graph(self.dep_graph),
                    self.declared_set() == self.defined_set()
                   ])

    def declared_set(self) -> set[str]:
        """ Get the set of tasks which have been declared, directly or indirectly """
        return set(self.dep_graph.nodes)

    def defined_set(self) -> set[str]:
        """ get the set of tasks which are explicitly defined """
        return set(self.tasks.keys())

    def update_state(self, task:str|TaskBase_i|DootTaskArtifact, state:TaskStateEnum):
        """ update the state of a task in the dependency graph """
        logging.debug("Updating Task State: %s -> %s", task, state)
        match task, state:
            case str(), self.state_e() if task in self.dep_graph:
                self.dep_graph.nodes[task]['state'] = state
            case TaskBase_i(), self.state_e() if task.name in self.dep_graph:
                self.dep_graph.nodes[task.name]['state'] = state
            case DootTaskArtifact(), self.state_e() if task in self.dep_graph:
                self.dep_graph.nodes[task]['state'] = state
            case _, _:
                raise doot.errors.DootTaskTrackingError("Bad task update state args", task, state)

    def task_state(self, task:str) -> TaskStateEnum:
        """ Get the state of a task """
        return self.dep_graph.nodes[task][STATE]

    def all_states(self) -> dict:
        """ Get a dict of all tasks, and their current state """
        nodes = self.dep_graph.nodes
        return {x: y[STATE] for x,y in nodes.items()}

    def write(self, target:pl.Path) -> None:
        """ Write the dependency graph to a file """
        raise NotImplementedError()

    def read(self, target:pl.Path) -> None:
        """ Read the dependency graph from a file """
        raise NotImplementedError()
