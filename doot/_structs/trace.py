#!/usr/bin/env python3
"""


"""

# Imports:
##-- builtin imports
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
from pydantic import BaseModel, Field, field_validator, model_validator
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot.errors
from doot.enums import Report_f, TaskMeta_f

# ##-- end 1st party imports

##-- end builtin imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class TraceRecord(BaseModel):
    message : str
    flags   : Report_f
    args    : list[Any]                = []
    time    : datetime.datetime        = Field(default_factory=datetime.datetime.now)

    @field_validator("flags", mode="before")
    def _valdiate_flags(cls, val):
        match val:
            case None:
                return Report_f.default
            case str() | list():
                return Report_f.build(val)
            case Report_f():
                return val
            case _:
                raise ValueError("Bad flags for TraceRecord", val)

    def __str__(self):
        match self.message:
            case str():
                return self.message.format(*self.args)
            case TaskSpec():
                return str(self.message.name)
            case _:
                return str(self.message)

    def __contains__(self, other:Report_f) -> bool:
        return all([x in self.flags for x in other])

    def __eq__(self, other:Report_f) -> bool:
        return self.flags == other

    def some(self, other:reportPositionEnum) -> bool:
        return any([x in self.flags for x in other])
