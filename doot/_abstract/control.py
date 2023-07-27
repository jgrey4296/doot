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
                    cast, final, overload, runtime_checkable, Generator, Literal)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from abc import abstractmethod
from typing import Generator, NewType
from collections import deque, defaultdict

from doot.enums import TaskStateEnum
from doot.structs import DootTaskArtifact
from doot._abstract.reporter import Reporter_i

@runtime_checkable
class TaskOrdering_p(Protocol):
    """ Protocol for tasks that have pre- and post- tasks"""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError(self.__class__, "name")

    @property
    @abstractmethod
    def priors(self) -> list:
        raise NotImplementedError(self.__class__, "priors")

    @property
    @abstractmethod
    def posts(self) -> list:
        raise NotImplementedError(self.__class__, "posts")

class TaskStatus_i:
    """ Interface for describing a tasks's current status """

    def __init__(self, get_log):
        self.get_log = get_log
        self.status = TaskStateEnum.WAIT
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
    state_e : enum.Enum = TaskStateEnum

    def __init__(self):
        self.tasks          = {}

    @abstractmethod
    def __iter__(self) -> Generator:
        raise NotImplementedError()

    @abstractmethod
    def __contains__(self, target:str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def add_task(self, task:None|TaskOrdering_p):
        raise NotImplementedError()

    @abstractmethod
    def queue_task(self, task:str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def update_task_state(self, task:str|TaskOrdering_p|DootTaskArtifact, state:TaskStateEnum) -> None:
        raise NotImplementedError()

    @abstractmethod
    def next_for(self, target:str) -> TaskOrdering_p|None:
        raise NotImplementedError()

    @abstractmethod
    def declared_set(self) -> set[str]:
        raise NotImplementedError()

    @abstractmethod
    def defined_set(self) -> set[str]:
        raise NotImplementedError()

class TaskRunner_i:
    """
    Run tasks, actions, and taskers
    """

    def __init__(self, tracker:TaskTracker_i, reporter:Reporter_i):
        self.tracker       = tracker
        self.reporter      = reporter
        self.teardown_list = []                     # list of tasks to teardown
        self.final_result  = TaskStateEnum.SUCCESS  # until something fails
        self._stop_running = False

    @abstractmethod
    def __call__(self, *tasks:str) -> bool:
        raise NotImplementedError()
