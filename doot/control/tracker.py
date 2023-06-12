#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

# import abc
# import datetime
# import enum
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
                    cast, final, overload, runtime_checkable)
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
from doot._abstract.control import TaskTracker_i, TaskRunner_i, TaskOrdering_i

ROOT : Final[str] = "__root"

class _TaskArtifact:

    def __init__(self, path:pl.Path):
        self._path = path

    def __hash__(self):
        return hash(self._path)

    def __repr__(self):
        type = "Definite" if self.is_definite() else "Indefinite"
        return f"<{type} TaskArtifact: {self._path.name}>"

    def __str__(self):
        return str(self._path)

    def __eq__(self, other):
        match other:
            case _TaskArtifact():
                return self._path == other._path
            case _:
                return False

    def is_definite(self):
        return self._path.stem not in "*?"

    def matches(self, other):
        match other:
            case _TaskArtifact() if not (other.is_definite() and self.is_definite()):
                parents_match = self._path.parent == other._path.parent
                exts_match    = self._path.suffix == other._path.suffix
                return parents_match and exts_match
            case _:
                raise TypeError(other)

    def exists(self):
        return self._path.exists()

class DootTracker(TaskTracker_i):
    """
    track dependencies in a networkx digraph,
    successors of a node are its dependencies,

    Uses a simple dsl for dependencies:
    file:(.+) -> specific file/path dependency
    file:(.+)/(?).(ext) -> single file/path wildcard
    file:(.+)/(+).(ext) -> multi-file/path un-grouped wildcard (n tasks for n files)
    file:(.+)/(*).(ext) -> multi-file/path grouped wildcard (1 task for n files together)

    (task:)?(.+) -> task dep

    """

    def __init__(self, shadowing=False):
        super().__init__() # tasks
        self.artifacts       = {}
        self.dep_graph       = nx.DiGraph()
        self.produce_mapping = defaultdict(set)
        self.queued_path     = []
        self.execution_path  = []
        self.shadowing       = shadowing

        self.dep_graph.add_node(ROOT, state=self.state_e.WAIT)

    def __iter__(self) -> Generator:
        while bool(self.queued_path):
            yield self.next_for()

    def __contains__(self, target):
        return target in self.tasks

    def _fixup_artifact_edges(self):
        """ connect generalised file products to specific """
        indefinite_nodes = [x for x in self.dep_graph.nodes if isinstance(x, _TaskArtifact) and not x.is_definite()]
        for node in self.dep_graph.nodes:
            match node:
                case str():
                    pass
                case _TaskArtifact() if node.is_definite():
                    for x in indefinite_nodes:
                        if x.matches(node):
                            self.dep_graph.add_edge(x, node)

                case _TaskArtifact():
                    pass
                case _:
                    raise TypeError(node)

    def add_task(self, task:None|tuple|Tasker|Task, no_root_connection=False):
        """ add a task description into the tracker,
        connecting it with its dependencies and tasks that depend on it
        """
        match task:
            case None:
                return
            case TaskOrdering_i():
                pass
            case (spec, cls):
                task = cls(spec)

        match task.name in self.tasks, self.shadowing:
            case True, False:
                raise KeyError("Task with Duplicate Name not added: ", task.name)
            case True, True:
                logging.warning("Task Shadowed by Duplicate Name: %s", task.name)

        self.tasks[task.name] = task
        task_state = self.state_e.READY if not bool(task.priors) else self.state_e.DEFINED
        self.dep_graph.add_node(task.name, state=task_state)
        if not no_root_connection:
            self.dep_graph.add_edge(ROOT, task.name)

        for pre in task.priors:
            edge_type = "task"
            match pre:
                case str() if pre not in self.dep_graph:
                    self.dep_graph.add_node(pre, state=self.state_e.DECLARED)
                case pl.Path():
                    pre = _TaskArtifact(pre)
                    edge_type = "artifact"
                    if pre not in self.dep_graph:
                        self.artifacts[str(pre)] = pre
                        self.dep_graph.add_node(pre, state=self.state_e.ARTIFACT)
                # TODO handle other artifacts?

            self.dep_graph.add_edge(task.name, pre, type=edge_type)

        for post in task.posts:
            edge_type = "task"
            match post:
                case str() if post not in self.dep_graph:
                    self.dep_graph.add_node(post, state=self.state_e.DECLARED)
                case pl.Path():
                    post      = _TaskArtifact(post)
                    edge_type = "artifact"
                    if post not in self.dep_graph:
                        self.artifacts[str(post)] = post
                        self.dep_graph.add_node(post, state=self.state_e.ARTIFACT)

            self.dep_graph.add_edge(post, task.name, type=edge_type)

        # TODO connect any specific paths to general paths
        # eg: test.file -> *.file

    def next_for(self, target:None|str=None) -> None|Tasker|Task:
        """ ask for the next task that should be performed """
        if target and target not in self.queued_path:
            self.queued_path.append(target)

        complete_states = {self.state_e.SUCCESS, self.state_e.EXISTS}
        focus             = None
        nodes             = self.dep_graph.nodes
        adj               = dict(self.dep_graph.adjacency())
        while bool(self.queued_path):
            focus        = self.queued_path[-1]
            match self.task_state(focus):
                case self.state_e.SUCCESS:
                    self.queued_path.pop()
                    self.queued_path += self.dep_graph.pred[focus]
                case self.state_e.EXISTS:
                    self.queued_path.pop()
                case self.state_e.FAILURE:
                    self.queued_path = []
                    return None
                case self.state_e.READY if focus in self.execution_path:
                    logging.warning("Task %s attempted to be run twice", focus)
                    self.update_task_state(focus, self.state_e.FAILURE)

                case self.state_e.READY:
                    self.execution_path.append(focus)
                    return self.tasks.get(focus, None)
                case self.state_e.ARTIFACT if focus.is_definite() and focus.exists():
                    self.queue_path.pop()
                    self.update_task_state(focus, self.state_e.EXISTS)
                case self.state_e.ARTIFACT:
                    dependencies = list(adj[focus].keys())
                    incomplete   = list(filter(lambda x: self.task_state(x) not in complete_states, dependencies))
                    if bool(incomplete):
                        self.queued_path += incomplete
                    else:
                        self.update_task_state(focus, self.state_e.EXISTS)
                case self.state_e.WAIT | self.state_e.DEFINED:
                    dependencies = list(adj[focus].keys())
                    incomplete   = list(filter(lambda x: self.task_state(x) not in complete_states, dependencies))
                    if bool(incomplete):
                        self.queued_path += incomplete
                    else:
                        self.update_task_state(focus, self.state_e.READY)
                case self.state_e.DECLARED:
                    logging.warning("Undefined Task in dependency path: %s", focus)
                    self.execution_path.append(focus)
                    self.update_task_state(focus, self.state_e.SUCCESS)
                case x:
                    raise TypeError("Unknown task state: ", x)

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

    def update_task_state(self, task, state):
        """ update the state of a task in the dependency graph """
        match task, state:
            case str(), self.state_e():
                self.dep_graph.nodes[task]['state'] = state
            case TaskOrdering_i(), self.state_e():
                self.dep_graph.nodes[task.name]['state'] = state
            case _TaskArtifact(), _:
                pass
            case _, _:
                raise TypeError("Bad task update state args", task, state)

    def task_state(self, task:str) -> Enum:
        """ Get the state of a task """
        return self.dep_graph.nodes[task]['state']

    def all_states(self) -> dict:
        """ Get a dict of all tasks, and their current state """
        nodes = self.dep_graph.nodes
        return {x: y['state'] for x,y in nodes.items()}

    def write(self, target):
        """ Write the dependency graph to a file """
        raise NotImplementedError()

    def read(self, target):
        """ Read the dependency graph from a file """
        raise NotImplementedError()
