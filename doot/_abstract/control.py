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

from collections import deque

class TaskStateEnum(enum.Enum):
    SUCCESS         = enum.auto()
    FAILURE         = enum.auto()
    WAIT            = enum.auto()
    READY           = enum.auto()
    INIT            = enum.auto()
    TEARDOWN        = enum.auto()
    DEFINED         = enum.auto()
    DECLARED        = enum.auto()
    ARTIFACT        = enum.auto()
    EXISTS          = enum.auto()

class TaskOrdering_i:

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def priors(self) -> list:
        raise NotImplementedError()

    @property
    def posts(self) -> list:
        raise NotImplementedError()


class TaskStatus_i:

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

    def get_error_message(self):
        '''return str with error message'''
        return self.error_reason

class TaskTracker_i:
    """
    Track tasks that have run, need to run, are running,
    and have failed.
    Does not execute anything itself
    """
    state_e = TaskStateEnum

    def __init__(self):
        self.tasks          = {}

    def add_task(self, task:None|Tasker|Task):
        raise NotImplementedError()

    def update_task_state(self, task, state):
        raise NotImplementedError()

    def next_for(self, target:str) -> Tasker|Task:
        raise NotImplementedError()

    def __iter__(self) -> Generator:
        raise NotImplementedError()

    def __contains__(self, target:str) -> bool:
        raise NotImplementedError()

    def declared_set(self) -> set[str]:
        raise NotImplementedError()

    def defined_set(self) -> set[str]:
        raise NotImplementedError()

class TaskRunner_i:
    """
    Run tasks, actions, and taskers
    """

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
