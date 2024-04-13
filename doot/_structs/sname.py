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
from doot._structs.structured_name import StructuredName
from doot._structs.task_name import DootTaskName
from doot._structs.code_ref import DootCodeReference

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskFlags]

@dataclass(eq=False, slots=True)
class DootStructuredName(StructuredName):
    """ A Complex name class for identifying tasks and classes.

      Classes are the standard form used in importlib: "module.path:ClassName"
      Tasks use a double colon to separate head from tail name: "group.name::TaskName"

    """
    head            : list[str]          = field(default_factory=list)
    tail            : list[str]          = field(default_factory=list)

    separator       : str                = field(default=doot.constants.patterns.TASK_SEP, kw_only=True)
    subseparator    : str                = field(default=".", kw_only=True)

    @staticmethod
    def build(name:str|DootStructuredName|type) -> DootStructuredName:
        match name:
            case DootStructuredName():
                return name
            case type():
                return DootCodeReference.build(name)
            case str() if doot.constants.patterns.TASK_SEP in name:
                return DootTaskName.build(name)
            case str() if doot.constants.patterns.IMPORT_SEP in name:
                return DootTaskName.build(name)
            case _:
                raise doot.errors.DootError("Tried to build a name from a bad value", name)
