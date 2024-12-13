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
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from importlib.metadata import EntryPoint
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Self, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Maybe
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
from doot._abstract.cmd import Command_i
from doot._abstract.protocols import SpecStruct_p
from doot._abstract.task import Job_i

# ##-- end 1st party imports


##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@runtime_checkable
class Loader_p[T](Protocol):

    def get_loaded(self, group:str, name:str) -> Maybe[str]:
        pass

    def setup(self, data:ChainGuard) -> Self:
        pass

    def load(self) -> ChainGuard[T]:
        pass

PluginLoader_p        = Loader_p[EntryPoint]
CommandLoader_p       = Loader_p[Command_i]
TaskLoader_p          = Loader_p[SpecStruct_p]
type Loaders_p = CommandLoader_p | PluginLoader_p | TaskLoader_p
