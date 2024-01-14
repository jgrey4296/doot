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
from doot._structs.artifact import DootTaskArtifact
from doot._structs.task_spec import DootTaskSpec
from doot._abstract.reporter import ReportLine_i, Reporter_i
from doot._abstract.policy import FailPolicy_p
from doot._abstract.task import TaskBase_i

class TaskTracker_i:
    """
    Track tasks that have run, need to run, are running,
    and have failed.
    Does not execute anything itself
    """
    state_e : TypeAlias = TaskStateEnum

    @abstractmethod
    def __bool__(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def __len__(self) -> int:
        raise NotImplementedError()

    @abstractmethod
    def __iter__(self) -> Generator:
        raise NotImplementedError()

    @abstractmethod
    def __contains__(self, target:str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def add_task(self, task:DootTaskSpec|TaskBase_i):
        raise NotImplementedError()

    @abstractmethod
    def queue_task(self, task:str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def update_state(self, task:str|DootTaskName|DootTaskSpec|TaskBase_i|DootTaskArtifact, state:TaskStateEnum) -> None:
        raise notimplementederror()

    @abstractmethod
    def next_for(self, target:str) -> TaskBase_i|DootTaskArtifact|None:
        raise NotImplementedError()

    @abstractmethod
    def declared_set(self) -> set[str]:
        raise NotImplementedError()

    @abstractmethod
    def defined_set(self) -> set[str]:
        raise NotImplementedError()

class TaskRunner_i:
    """
    Run tasks, actions, and jobs
    """

    @abstractmethod
    def __init__(self, *, tracker:TaskTracker_i, reporter:Reporter_i, policy:FailPolicy_p|None=None):
        pass

    @abstractmethod
    def __call__(self, *tasks:str) -> bool:
        raise NotImplementedError()
