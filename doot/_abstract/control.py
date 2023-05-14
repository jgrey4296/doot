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

class ExecutionResult(enum.Enum):
    # execution result.
    SUCCESS = enum.auto()
    FAILURE = enum.auto()
    ERROR   = enum.auto()

class TaskStatus_i:
    """Result object for Dependency.get_status.

    @ivar status: (str) one of "run", "up-to-date" or "error"
    """

    def __init__(self, get_log):
        self.get_log = get_log
        self.status = 'up-to-date'
        # save reason task is not up-to-date
        self.reasons = defaultdict(list)
        self.error_reason = None

    def add_reason(self, reason, arg, status='run'):
        """sets state and append reason for not being up-to-date
        :return boolean: processing should be interrupted
        """
        self.status = status
        if self.get_log:
            self.reasons[reason].append(arg)
        return not self.get_log

    def set_reason(self, reason, arg):
        """sets state and reason for not being up-to-date
        :return boolean: processing should be interrupted
        """
        self.status = 'run'
        if self.get_log:
            self.reasons[reason] = arg
        return not self.get_log

    def get_error_message(self):
        '''return str with error message'''
        return self.error_reason

class TaskTracker_i:
    """
    Track tasks that have run, need to run, are running,
    and have failed.
    Does not execute anything itself
    """

    def __init__(self, tasks, targets, selected_tasks):
        self.tasks          = tasks
        self.targets        = targets
        self.selected_tasks = selected_tasks

        self.nodes          = {}      # key task-name, value: _ExecNode
                                      # queues
        self.waiting        = set()   # of _ExecNode
        self.ready          = deque() # of _ExecNode

    def build_dependencies(self):
        pass

    def update_dependencies(self, info):
        pass


class TaskRunner_i:
    """
    Run tasks, actions, and taskers
    """

    def __init__(self, reporter):
        self.reporter       = reporter
        self.teardown_list = []  # list of tasks to be teardown
        self.final_result  = SUCCESS  # until something fails
        self._stop_running = False


    def execute_task(self, task):
        """execute task's actions"""
        pass

    def process_task_result(self, node, base_fail):
        """handles result"""
        pass

    def run_tasks(self, *tasks):
        pass

    def teardown(self):
        """run teardown from all tasks"""
        pass

    def finish(self):
        """finish running tasks"""
        pass
