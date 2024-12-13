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
from jgdv.structs.chainguard import ChainGuard
from importlib.metadata import EntryPoint

from doot._abstract.protocols import SpecStruct_p
from doot._abstract.cmd import Command_i
from doot._abstract.task import Job_i

_T = TypeVar("_T")

@runtime_checkable
class Loader_p(Protocol, Generic[_T]):

    def get_loaded(group:str, name:str) -> None|str:
        pass

    def setup(self, data:ChainGuard) -> Self:
        pass

    def load(self) -> ChainGuard[_T]:
        pass



PluginLoader_p        = Loader_p[EntryPoint]
CommandLoader_p       = Loader_p[Command_i]
TaskLoader_p          = Loader_p[SpecStruct_p]
Loaders_p : TypeAlias = CommandLoader_p | PluginLoader_p | TaskLoader_p
