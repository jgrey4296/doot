#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


class ExecNode:
    """Each task will have an instance of this.
    This used to keep track of waiting events and the generator for dep nodes

    @ivar run_status (str): contains the result of Dependency.get_status().status
            modified by runner, value can be:
           - None: not processed yet
           - run: task is selected to be executed (it might be running or
                   waiting for setup)
           - ignore: task wont be executed (user forced deselect)
           - up-to-date: task wont be executed (no need)
           - done: task finished its execution
    """
    def __init__(self, task, parent):
        self.task = task
        # list of dependencies not processed by _add_task yet
        self.task_dep = task.task_dep[:]
        self.calc_dep = task.calc_dep.copy()

        # ancestors are used to detect cyclic references.
        # it does not contain a list of tasks that depends on this node
        # for that check the attribute waiting_me
        self.ancestors = []
        if parent:
            self.ancestors.extend(parent.ancestors)
        self.ancestors.append(task.name)

        # Wait for a task to be selected to its execution
        # checking if it is up-to-date
        self.wait_select = False

        # Wait for a task to finish its execution
        self.wait_run = set()  # task names
        self.wait_run_calc = set()  # task names

        self.waiting_me = set()  # ExecNode

        self.run_status = None
        # all ancestors that failed
        self.bad_deps = []
        self.ignored_deps = []

        # generator from TaskDispatcher._add_task
        self.generator = None

    def reset_task(self, task, generator):
        """reset task & generator after task is created by its own `loader`"""
        self.task = task
        self.task_dep = task.task_dep[:]
        self.calc_dep = task.calc_dep.copy()
        self.generator = generator

    def parent_status(self, parent_node):
        if parent_node.run_status == 'failure':
            self.bad_deps.append(parent_node)
        elif parent_node.run_status == 'ignore':
            self.ignored_deps.append(parent_node)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.task.name)

    def step(self):
        """get node's next step"""
        try:
            return next(self.generator)
        except StopIteration:
            return None
