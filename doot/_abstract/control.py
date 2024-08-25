#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from abc import abstractmethod
from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Literal, Mapping, Match,
                    MutableMapping, NewType, Protocol, Sequence, Tuple,
                    TypeAlias, TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 1st party imports
from doot._abstract.policy import FailPolicy_p
from doot._abstract.protocols import ArtifactStruct_p, SpecStruct_p
from doot._abstract.reporter import Reporter_p
from doot._abstract.task import Task_i
from doot.enums import ExecutionPolicy_e, TaskStatus_e
# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# ## Types
AbstractId                     : TypeAlias                   = "TaskName|TaskArtifact"
ConcreteId                     : TypeAlias                   = "TaskName|TaskArtifact"
AnyId                          : TypeAlis                    = "TaskName|TaskArtifact"
AbstractSpec                   : TypeAlias                   = "TaskSpec"
ConcreteSpec                   : TypeAlias                   = "TaskSpec"
AnySpec                        : TypeAlias                   = "TaskSpec"
Depth                          : TypeAlias                   = int
PlanEntry                      : TypeAlias                   = tuple[Depth, ConcreteId, str]

class TaskTracker_i:
    """
    Track tasks that have run, need to run, are running,
    and have failed.
    Does not execute anything itself
    """

    @abstractmethod
    def register_spec(self, *specs:AnySpec)-> None:
        pass

    @abstractmethod
    def queue_entry(self, name:str|AnyId|ConcreteSpec|Task_i, *, from_user:bool=False, status:None|TaskStatus_e=None) -> None|Node:
        pass

    @abstractmethod
    def get_status(self, task:ConcreteId) -> TaskStatus_e:
        pass

    @abstractmethod
    def set_status(self, task:ConcreteId|Task_i, state:TaskStatus_e) -> bool:
        pass

    @abstractmethod
    def next_for(self, target:None|str|ConcreteId=None) -> None|Task_i|"TaskArtifact":
        pass

    @abstractmethod
    def build_network(self) -> None:
        pass

    @abstractmethod
    def generate_plan(self, *, policy:None|ExecutionPolicy_e=None) -> list[PlanEntry]:
        pass

class TaskRunner_i:
    """
    Run tasks, actions, and jobs
    """

    @abstractmethod
    def __enter__(self) -> Any:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        pass

    @abstractmethod
    def __init__(self, *, tracker:TaskTracker_i, reporter:Reporter_p, policy:FailPolicy_p|None=None):
        pass

    @abstractmethod
    def __call__(self, *tasks:str) -> bool:
        pass
