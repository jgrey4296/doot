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
import doot
import doot.errors
from doot.enums import TaskFlags, ReportEnum

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskFlags]

def aware_splitter(x, sep="."):
    match x:
        case str():
            return x.split(sep)
        case _:
            return [x]

@dataclass(eq=False, slots=True)
class DootStructuredName:
    """ A Complex name class for identifying tasks and classes.

      Classes are the standard form used in importlib: "module.path:ClassName"
      Tasks use a double colon to separate head from tail name: "group.name::TaskName"

    """
    head            : list[str]          = field(default_factory=list)
    tail            : list[str|UUID]     = field(default_factory=list)

    separator       : str                = field(default=doot.constants.patterns.TASK_SEP, kw_only=True)
    subseparator    : str                = field(default=".", kw_only=True)

    def __post_init__(self):
        sub_split = ftz.partial(aware_splitter, sep=self.subseparator)
        match self.head:
            case None | []:
                self.head = ["default"]
            case ["tasks", x] if x.startswith('"') and x.endswith('"'):
                self.head = ftz.reduce(lambda x, y: x + y, map(sub_split, x[1:-1]))
            case ["tasks", *xs]:
                self.head = ftz.reduce(lambda x, y: x + y, map(sub_split, xs))
            case list():
                self.head = ftz.reduce(lambda x, y: x + y, map(sub_split, self.head))
            case str():
                self.head = self.head.split(self.subseparator)
            case _:
                self.head = [self.head]

        match self.tail:
            case None | []:
                self.tail = ["default"]
            case list():
                self.tail = ftz.reduce(lambda x, y: x + y, map(sub_split, self.tail))
            case str():
                self.tail = self.tail.split(self.subseparator)
            case _:
                self.tail = [self.tail]

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return self.head_str + self.separator + self.tail_str

    def __lt__(self, other) -> bool:
        """ Compare two names, return true if other is a subname of this name
        eg: a.b.c < a.b.c.d
        """
        match other:
            case str():
                other = DootStructuredName.from_str(other)
            case DootStructuredName():
                pass
            case _:
                return False

        for x,y in zip(self.head, other.head):
            if x != y:
                return False

        for x,y in zip(self.tail, other.tail):
            if x != y:
                return False

        return True

    def __contains__(self, other:str):
        return str(other) in str(self)

    def __eq__(self, other):
        return str(self) == str(other)

    def tail_str(self):
        return self.subseparator.join(str(x) for x in self.tail)

    def head_str(self):
        return self.subseparator.join(str(x) for x in self.head)
