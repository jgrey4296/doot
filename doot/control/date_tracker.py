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
    TASK     = enum.auto()
    ARTIFACT = enum.auto()

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

    def write(self, target:pl.Path) -> None:
        """ Write the dependency graph to a file """
        raise NotImplementedError()

    def read(self, target:pl.Path) -> None:
        """ Read the dependency graph from a file """
        raise NotImplementedError()

    def task_state(self, task:str|DootStructuredName|pl.Path, query_from=None) -> TaskStateEnum:
        """ Get the state of a task """
        if query_from is not None:
            query_date = self.last_ran.get(query_from, datetime.datetime.now())
            task_date  = self.last_ran.get(str(task), None)
            if task_date and query_date <= task_date:
                self.update_state(task, TaskStateEnum.DEFINED)
            elif task_date and task_date <= query_date:
                self.update_state(task, TaskStateEnum.SUCCESS)

        if str(task) in self.dep_graph.nodes:
            return self.dep_graph.nodes[str(task)][STATE]
        else:
            raise doot.errors.DootTaskTrackingError("Unknown Task state requested: %s", task)
