#!/usr/bin/env python2
"""

See EOF for license/metadata/notes as applicable
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
import string
import time
import types
import weakref
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload, Self,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import decorator
import more_itertools as mitz
from pydantic import BaseModel, Field, field_validator, model_validator
from tomlguard import TomlGuard
from jgdv.structs.code_ref import CodeReference
from jgdv.structs.dkey import DKeyFormatter, DKey, DKeyMark_e
from jgdv.structs.dkey.key import REDIRECT_SUFFIX, CONV_SEP
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import Key_p, SpecStruct_p, Buildable_p
from doot._structs.task_name import TaskName
from doot.utils.decorators import DecorationUtils, DootDecorator

# ##-- end 1st party imports

##-- type checking
if TYPE_CHECKING:
    DootLocations:TypeAlias = Any
##-- end type checking

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

KEY_PATTERN                                 = doot.constants.patterns.KEY_PATTERN
MAX_KEY_EXPANSIONS                          = doot.constants.patterns.MAX_KEY_EXPANSIONS
STATE_TASK_NAME_K                           = doot.constants.patterns.STATE_TASK_NAME_K

PATTERN         : Final[re.Pattern]         = re.compile(KEY_PATTERN)
FAIL_PATTERN    : Final[re.Pattern]         = re.compile("[^a-zA-Z_{}/0-9-]")
FMT_PATTERN     : Final[re.Pattern]         = re.compile("[wdi]+")
EXPANSION_HINT  : Final[str]                = "_doot_expansion_hint"
HELP_HINT       : Final[str]                = "_doot_help_hint"
FORMAT_SEP      : Final[str]                = ":"
CHECKTYPE       : TypeAlias                 = None|type|types.GenericAlias|types.UnionType
CWD_MARKER      : Final[str]                = "__cwd"


class TaskNameDKey(SingleDKey, mark=DKeyMark_e.TASK, tparam="t"):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = TaskName.build
        self._typecheck = TaskName

class PathSingleDKey(SingleDKey, mark=DKeyMark_e.PATH):
    """ for paths that are just a single key of a larger string
    eg: `temp`
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = pl.Path
        self._typecheck       = pl.Path
        self._relative        = kwargs.get('relative', False)

    def extra_sources(self):
        return [doot.locs]

    def expand(self, *sources, **kwargs) -> None|Pl.Path:
        """ Expand subkeys, format the multi key
          Takes a variable number of sources (dicts, tomlguards, specs, dootlocations..)
        """
        logging.debug("Single Path Expand")
        if self == CWD_MARKER:
            return pl.Path.cwd()
        match super().expand(*sources, **kwargs):
            case None:
                return self._fallback
            case pl.Path() as x:
                return x
            case _:
                raise TypeError("Path Key shouldn't be able to produce a non-path")

    def _expansion_hook(self, value) -> None|pl.Path:
        match value:
            case None:
                return None
            case pl.Path() as x if self._relative and x.is_absolute():
                raise ValueError("Produced an absolute path when it is marked as relative", x)
            case pl.Path() as x if self._relative:
                return x
            case pl.Path() as x:
                logging.debug("Normalizing Single Path Key: %s", value)
                return doot.locs.normalize(x)
            case x:
                raise TypeError("Path Expansion did not produce a path", x)

class PathMultiDKey(MultiDKey, mark=DKeyMark_e.PATH, tparam="p", multi=True):
    """
    A MultiKey that always expands as a path,
    eg: `{temp}/{name}.log`
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = pl.Path
        self._typecheck       = pl.Path
        self._relative        = kwargs.get('relative', False)

    def extra_sources(self):
        return [doot.locs]

    def keys(self) -> list[Key_p]:
        subkeys = [DKey(key.key, fmt=key.format, conv=key.conv, implicit=True) for key in self._subkeys]
        return subkeys

    def expand(self, *sources, fallback=None, **kwargs) -> None|pl.Path:
        """ Expand subkeys, format the multi key
          Takes a variable number of sources (dicts, tomlguards, specs, dootlocations..)
        """
        match super().expand(*sources, fallback=fallback, **kwargs):
            case None:
                return self._fallback
            case pl.Path() as x:
                return x
            case _:
                raise TypeError("Path Key shouldn't be able to produce a non-path")

    def _expansion_hook(self, value) -> None|pl.Path:
        logging.debug("Normalizing Multi path key: %s", value)
        match value:
            case None:
                return None
            case pl.Path() as x if self._relative and x.is_absolute():
                raise ValueError("Produced an absolute path when it is marked as relative", x)
            case pl.Path() as x  if self._relative:
                return x
            case pl.Path() as x:
                logging.debug("Normalizing Single Path Key: %s", value)
                return doot.locs.normalize(x)
            case x:
                raise TypeError("Path Expansion did not produce a path", x)

class PostBoxDKey(SingleDKey, mark=DKeyMark_e.POSTBOX, tparam="b"):
    """ A DKey which expands from postbox tasknames  """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._expansion_type  = list
        self._typecheck = list

    def expand(self, *sources, fallback=None, **kwargs):
        # expand key to a task name
        target = None
        # get from postbox
        result = None
        # return result
        raise NotImplementedError()
