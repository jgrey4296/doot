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

from typing import Self
from abc import abstractmethod
from tomler import Tomler
from importlib.metadata import EntryPoint

from doot._abstract.cmd import Command_i
from doot._abstract.tasker import Tasker_i


@runtime_checkable
class PluginLoader_p(Protocol):
    """ Base for the first things loaded: plugins."""

    @abstractmethod
    def setup(self, extra_config:Tomler) -> Self:
        raise NotImplementedError()

    @abstractmethod
    def load(self) -> Tomler[EntryPoint]:
        raise NotImplementedError()

@runtime_checkable
class CommandLoader_p(Protocol):
    """ Base for the second thing loaded: commands """

    @abstractmethod
    def setup(self, plugins:Tomler) -> Self:
        raise NotImplementedError()

    @abstractmethod
    def load(self) -> Tomler[Command_i]:
        raise NotImplementedError()

@runtime_checkable
class TaskLoader_p(Protocol):
    """ Base for the final thing loaded: user tasks """
    _task_collection : list
    _build_failures  : list
    _task_class      : type

    @abstractmethod
    def setup(self, plugins:Tomler) -> Self:
        raise NotImplementedError()

    @abstractmethod
    def load(self) -> Tomler[tuple[dict, Tasker_i]]:
        raise NotImplementedError()


Loaders_p : TypeAlias = CommandLoader_p | PluginLoader_p | TaskLoader_p
