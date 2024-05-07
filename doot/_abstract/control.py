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

from doot.enums import TaskStatus_e

from doot._abstract.reporter import Reporter_p
from doot._abstract.policy import FailPolicy_p
from doot._abstract.task import Task_i
from doot._abstract.structs import ArtifactStruct_p, SpecStruct_p

class TaskTracker_i:
    """
    Track tasks that have run, need to run, are running,
    and have failed.
    Does not execute anything itself
    """

    @abstractmethod
    def register_spec(self, task:SpecStruct_p|Task_i):
        raise NotImplementedError()

    @abstractmethod
    def queue_entry(self, task:str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def set_status(self, task:str|DootTaskName|SpecStruct_p|Task_i|ArtifactStruct_p, state:TaskStatus_e) -> None:
        raise notimplementederror()

    @abstractmethod
    def next_for(self, target:str) -> Task_i|ArtifactStruct_p|None:
        raise NotImplementedError()

    @abstractmethod
    def build_network(self) -> None:
        pass
class TaskRunner_i:
    """
    Run tasks, actions, and jobs
    """

    @abstractmethod
    def __init__(self, *, tracker:TaskTracker_i, reporter:Reporter_p, policy:FailPolicy_p|None=None):
        pass

    @abstractmethod
    def __call__(self, *tasks:str) -> bool:
        raise NotImplementedError()
