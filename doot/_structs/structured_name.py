#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
# import abc
import datetime
import enum
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import more_itertools as mitz
from pydantic import BaseModel, Field, field_validator
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import Buildable_p, Nameable_p, ProtocolModelMeta
from doot.enums import Report_f, TaskMeta_f

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskMeta_f]
TailEntry     : TypeAlias  = str|int|UUID

def aware_splitter(x, sep=".") -> list[str]:
    match x:
        case str():
            return x.split(sep)
        case _:
            return [x]

class StructuredName(BaseModel, Nameable_p, Buildable_p, metaclass=ProtocolModelMeta):
    """ A Complex name class for identifying tasks and classes.

      Classes are the standard form used in importlib: "module.path:ClassName"
      Tasks use a double colon to separate head from tail name: "group.name::TaskName"

    """
    head             : list[str]              = []
    tail             : list[TailEntry]        = []

    _separator       : ClassVar[str]          = doot.constants.patterns.TASK_SEP
    _subseparator    : ClassVar[str]          = "."

    @staticmethod
    def build(val:str) -> StructuredName:
        match val.split(StructuredName._separator):
            case [head, tail]:
                return StructuredName(head=[head], tail=[tail])
            case _:
                raise ValueError("Bad value for building a name from", val)

    @field_validator("head", mode="before")
    def _process_head(cls, head):
        sub_split = ftz.partial(aware_splitter, sep=cls._subseparator)
        match head:
            case None | []:
                head = ["default"]
            case ["tasks", x] if x.startswith('"') and x.endswith('"'):
                head = ftz.reduce(lambda x, y: x + y, map(sub_split, x[1:-1]))
            case ["tasks", *xs]:
                head = ftz.reduce(lambda x, y: x + y, map(sub_split, xs))
            case list():
                head = ftz.reduce(lambda x, y: x + y, map(sub_split, head))
            case _:
                raise ValueError("Bad Head Value", head)

        return head

    @field_validator("tail", mode="before")
    def _process_tail(cls, tail):
        sub_split = ftz.partial(aware_splitter, sep=cls._subseparator)
        match tail:
            case None | []:
                tail = ["default"]
            case list():
                tail = ftz.reduce(lambda x, y: x + y, map(sub_split, tail))
            case _:
                raise ValueError("Bad Tail Value", tail)
        return tail

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return self._separator.join([self.head_str(), self.tail_str()])

    def __eq__(self, other):
        return str(self) == str(other)

    def __lt__(self, other) -> bool:
        """ test for hierarhical ordering of names
        eg: self(a.b.c) < other(a.b.c.d)
        ie: other ∈ self
        """
        match other:
            case str():
                other = StructuredName.build(other)
            case StructuredName():
                pass
            case _:
                return False

        if len(self.head) != len(other.head):
            return False
        if len(self.tail) >= len(other.tail):
            return False

        for x,y in zip(self.head, other.head):
            if x != y:
                return False

        for x,y in zip(self.tail, other.tail):
            if x != y:
                return False

        return True

    def __le__(self, other) -> bool:
        return (self == other) or (self < other)

    def __contains__(self, other) -> bool:
        """ test for conceptual containment of names
        other(a.b.c) ∈ self(a.b) ?
        ie: self < other
        """
        match other:
            case str():
                return other in str(self)
            case StructuredName() if len(self.tail) > len(other.tail):
                # a.b.c.d is not in a.b
                return False
            case StructuredName():
                head_matches = all(x==y for x,y in zip(self.head, other.head))
                tail_matches = all(x==y for x,y in zip(self.tail, other.tail))
                return head_matches and tail_matches

    def tail_str(self) -> str:
        return self._subseparator.join(str(x) for x in self.tail)

    def head_str(self) -> str:
        return self._subseparator.join(str(x) for x in self.head)
