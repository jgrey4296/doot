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

class DootTracker(TaskTracker_i):
    """
    track dependencies in a networkx digraph,
    successors of a node are its dependencies,

    """

    def __init__(self):
        super().__init__() # tasks
        self.dep_graph       = nx.DiGraph()
        self.produce_mapping = defaultdict(set)
        self.queued_path     = []
        self.execution_path  = []

    def add_task(self, task:None|tuple|Tasker|Task):
        match task:
            case None:
                return
            case TaskOrdering_i():
                pass
            case (spec, cls):
                task = cls(spec)

        if task.name in self.tasks:
            logging.warning("Task with Duplicate Name not added: %s", task.name)
            return

        self.tasks[task.name] = task
        task_state = self.state_e.READY if not bool(task.priors) else self.state_e.DEFINED
        self.dep_graph.add_node(task.name, state=task_state)

        for pre in task.priors:
            if pre not in self.dep_graph:
                self.dep_graph.add_node(pre, state=self.state_e.DECLARED)
            self.dep_graph.add_edge(task.name, pre)
        for post in task.posts:
            if post not in self.dep_graph:
                self.dep_graph.add_node(post, state=self.state_e.DECLARED)
            self.dep_graph.add_edge(post, task.name)

    def validate(self) -> bool:
        return all([nx.is_directed_acyclic_graph(self.dep_graph),
                    self.declared_set() == self.defined_set()
                   ])

    def declared_set(self) -> set[str]:
        return set(self.dep_graph.nodes)

    def defined_set(self) -> set[str]:
        return set(self.tasks.keys())

    def update_task_state(self, task, state):
        match task, state:
            case str(), self.state_e():
                self.dep_graph.nodes[task]['state'] = state
            case TaskOrdering_i(), self.state_e():
                self.dep_graph.nodes[task.name]['state'] = state
            case _, _:
                raise TypeError("Bad task update state args", task, state)


    def next_for(self, target:None|str=None) -> None|Tasker|Task:
        if target and target not in self.queued_path:
            self.queued_path.append(target)

        incomplete_states = {self.state_e.DEFINED, self.state_e.WAIT, self.state_e.DECLARED}
        exit              = False
        focus             = None
        nodes             = self.dep_graph.nodes
        adj               = dict(self.dep_graph.adjacency())
        while bool(self.queued_path) and not exit:
            focus        = self.queued_path[-1]
            match self.task_state(focus):
                case self.state_e.SUCCESS:
                    self.queued_path.pop()
                case self.state_e.FAILURE:
                    self.queued_path = []
                    return None
                case self.state_e.READY:
                    self.execution_path.append(focus)
                    return self.tasks.get(focus, None)
                case self.state_e.WAIT | self.state_e.DEFINED:
                    dependencies = list(adj[focus].keys())
                    incomplete   = list(filter(lambda x: self.task_state(x) in incomplete_states, dependencies))
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


    def task_state(self, task:str) -> Enum:
        return self.dep_graph.nodes[task]['state']

    def all_states(self) -> dict:
        nodes = self.dep_graph.nodes
        return {x: y['state'] for x,y in nodes.items()}

    def __iter__(self) -> Generator:
        while bool(self.queued_path):
            yield self.next_for()

    def __contains__(self, target):
        return target in self.tasks

    def write(self, target):
        pass

    def read(self, target):
        pass

class DootRunner(TaskRunner_i):

    def __init__(self, tracker, reporter):
        self.tracker       = tracker
        self.reporter      = reporter
        self.teardown_list = []  # list of tasks to be teardown
        self.final_result  = SUCCESS  # until something fails
        self._stop_running = False

    def __call__(self, *tasks:str):
        raise NotImplementedError()

    def execute_task(self, task):
        """execute task's actions"""
        raise NotImplementedError()

    def process_task_result(self, node, base_fail):
        """handles result"""
        raise NotImplementedError()

    def teardown(self):
        """run teardown from all tasks"""
        raise NotImplementedError()

    def finish(self):
        """finish running tasks"""
        raise NotImplementedError()
