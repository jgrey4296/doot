#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import importlib
from tomlguard import TomlGuard
import doot.errors
import doot.constants
from doot.enums import TaskFlags, ReportEnum

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskFlags]

@dataclass
class DootTraceRecord:
    message : str                      = field()
    flags   : None|ReportEnum          = field()
    args    : list[Any]                = field(default_factory=list)
    time    : datetime.datetime        = field(default_factory=datetime.datetime.now)

    def __str__(self):
        match self.message:
            case str():
                return self.message.format(*self.args)
            case DootTaskSpec():
                return str(self.message.name)
            case _:
                return str(self.message)

    def __contains__(self, other:ReportEnum) -> bool:
        return all([x in self.flags for x in other])

    def __eq__(self, other:ReportEnum) -> bool:
        return self.flags == other

    def some(self, other:reportPositionEnum) -> bool:
        return any([x in self.flags for x in other])

"""

"""
