#!/usr/bin/env python3
"""


"""
# ruff: noqa:

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import collections
import contextlib
import hashlib
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref
import atexit # for @atexit.register
import faulthandler
# ##-- end stdlib imports

from jgdv.mixins.enum_builders import EnumBuilder_m
from doot.workflow._interface import TaskStatus_e, ArtifactStatus_e

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


class EdgeType_e(EnumBuilder_m, enum.Enum):
    """ Enum describing the possible edges of the task tracker's task network """

    TASK              = enum.auto() # task to task
    ARTIFACT_UP       = enum.auto() # abstract to concrete artifact
    ARTIFACT_DOWN     = enum.auto() # concrete to abstract artifact
    TASK_CROSS        = enum.auto() # Task to artifact
    ARTIFACT_CROSS    = enum.auto() # artifact to task

    default           = TASK

    @classmethod # type: ignore
    @property
    def artifact_edge_set(cls) -> set[enum.Enum]:
        return  {cls.ARTIFACT_UP, cls.ARTIFACT_DOWN, cls.TASK_CROSS}
# Vars:
MAX_LOOP                        : Final[int]                  = 100

EXPANDED                        : Final[str]                  = "expanded"  # Node attribute name
REACTIVE_ADD                    : Final[str]                  = "reactive-add"
ROOT                            : Final[str]                  = "root::_.$gen$" # Root node of dependency graph
EXPANDED                        : Final[str]                  = "expanded"  # Node attribute name
REACTIVE_ADD                    : Final[str]                  = "reactive-add"
CLEANUP                         : Final[str]                  = "cleanup"
ARTIFACT_EDGES                  : Final[set[EdgeType_e]]      = EdgeType_e.artifact_edge_set
DECLARE_PRIORITY                : Final[int]                  = 10
MIN_PRIORITY                    : Final[int]                  = -10
INITIAL_SOURCE_CHAIN_COUNT      : Final[int]                  = 10

SUCCESS_STATUSES : Final[set[TaskStatus_e|ArtifactStatus_e]]  = {
    TaskStatus_e.SUCCESS,
    TaskStatus_e.TEARDOWN,
    TaskStatus_e.DEAD,
    ArtifactStatus_e.EXISTS,
}

# Body:


class TaskTracker_p(Protocol):
    """
    Track tasks that have run, need to run, are running,
    and have failed.
    Does not execute anything itself
    """

    def register_spec(self, *specs:TaskSpec)-> None:
        pass

    def queue_entry(self, name:str|Ident|Concrete[TaskSpec], *, from_user:bool=False, status:Maybe[TaskStatus_e]=None) -> Maybe[Concrete[Ident]]:
        pass

    def get_status(self, task:Concrete[Ident]) -> TaskStatus_e:
        pass

    def set_status(self, task:Concrete[Ident]|Task_p, state:TaskStatus_e) -> bool:
        pass

    def next_for(self, target:Maybe[str|Concrete[Ident]]=None) -> Maybe[Actual]:
        pass

    def build_network(self) -> None:
        pass

    def generate_plan(self, *, policy:Maybe[ExecutionPolicy_e]=None) -> list[PlanEntry]:
        pass
