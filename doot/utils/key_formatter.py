#!/usr/bin/env python3
"""

key formatting:

- key.format()
- "{}".format(key)
- format(key, spec)

key -> str:
keep as a key if missing.
{x} -> {x}

expand to string if not missing:
{x} -> blah
respect format specs if not missing:
{x: <5} -> 'blah  '
keep format specs if missing:
{x: <5} -> {x: <5}

-----

key expansion:
- key.expand(fmtspec, spec=actionspec, state=state)
- key(spec, state)

key -> str by default.

key -> path|type if conversion spec
{x!p} -> pl.Path...
{x!t} -> dict() etc..

----

format(DKey, fmt) -> DKey.__format__ -> str
DKey.__format__   -> str
Dkey.format       -> KeyFormatter.fmt -> KF.expand -> KF.format -> str
DKey.expand       -> KF.expand -> KF.format -> KF.expand -> Any

See EOF for license/metadata/notes as applicable
"""

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
import string
import time
import types
import weakref
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import decorator
import more_itertools as mitz
from pydantic import BaseModel, Field, field_validator, model_validator
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import Key_p, SpecStruct_p
from doot._structs.code_ref import CodeReference
from doot.utils.decorators import DecorationUtils, DootDecorator
from doot.utils.chain_get import DootKeyGetter

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

KEY_PATTERN                                = doot.constants.patterns.KEY_PATTERN
MAX_KEY_EXPANSIONS                         = doot.constants.patterns.MAX_KEY_EXPANSIONS
STATE_TASK_NAME_K                          = doot.constants.patterns.STATE_TASK_NAME_K

PATTERN        : Final[re.Pattern]         = re.compile(KEY_PATTERN)
FAIL_PATTERN   : Final[re.Pattern]         = re.compile("[^a-zA-Z_{}/0-9-]")
EXPANSION_HINT : Final[str]                = "_doot_expansion_hint"
HELP_HINT      : Final[str]                = "_doot_help_hint"

def chained_get(key:str, *sources:dict|DootLocations) -> Any:
    """
      Get a key's value from an ordered sequence of potential sources
    """
    for source in sources:
        if source is None:
            continue
        replacement = source.get(key, None)
        if replacement is not None:
            return replacement

    return None

class KeyFormatter(string.Formatter):
    """
      A Formatter for expanding arguments based on action spec kwargs, and task state, and cli args
    """
    _fmt                = None

    SPEC   : Final[str] = "_spec"
    INSIST : Final[str] = "_insist"
    STATE  : Final[str] = "_state"
    LOCS   : Final[str] = "_locs"
    REC    : Final[str] = "_rec"

    @staticmethod
    def fmt(fmt:str|Key_p|pl.Path, /, *args, **kwargs) -> str:
        if not KeyFormatter._fmt:
            KeyFormatter._fmt = KeyFormatter()

        return KeyFormatter._fmt.format(fmt, *args, **kwargs)

    def format(self, fmt:str|Key_p|pl.Path, /, *args, **kwargs) -> str:
        """ expand and coerce keys """
        self._depth = 0
        match kwargs.get(self.SPEC, None):
            case None:
                kwargs['_spec'] = {}
            case x if hasattr(x, "params"):
                kwargs['_spec'] = x.params
            case x:
                raise TypeError("Bad Spec Type in Format Call", x)

        match fmt:
            case Key_p():
                fmt = fmt.form
                result = self.vformat(fmt, args, kwargs)
            case str():
                result = self.vformat(fmt, args, kwargs)
            # case pl.Path():
            #     result = str(ftz.reduce(pl.Path.joinpath, [self.vformat(x, args, kwargs) for x in fmt.parts], pl.Path()))
            case _:
                raise TypeError("Unrecognized expansion type", fmt)

        return result

    def get_value(self, key:str, args:list, kwargs:dict):
        """ lowest level handling of keys being expanded """
        logging.debug("Expanding: %s", key)
        if isinstance(key, int):
            return args[key]

        insist                = kwargs.get(self.INSIST, False)
        spec  : dict          = kwargs.get(self.SPEC, None) or {}
        state : dict          = kwargs.get(self.STATE, None) or {}
        locs  : DootLocations = kwargs.get(self.LOCS,  None)
        depth_check           = self._depth < MAX_KEY_EXPANSIONS
        rec_allowed           = kwargs.get(self.REC, False) and depth_check

        match (replacement:=DootKeyGetter.chained_get(key, spec, state, locs)):
            case None if insist:
                raise KeyError("Key Expansion Not Found")
            case None:
                return f"{{{key}}}"
            case Key_p() if depth_check:
                self._depth += 1
                return self.vformat(replacement.form, args, kwargs)
            case str() if rec_allowed:
                self._depth += 1
                return self.vformat(str(replacement), args, kwargs)
            case str():
                return replacement
            case pl.Path() if depth_check:
                self._depth += 1
                return ftz.reduce(pl.Path.joinpath, map(lambda x: self.vformat(x, args, kwargs), replacement.parts), pl.Path())
            case _:
                return str(replacement)
                # raise TypeError("Replacement Value isn't a string", args, kwargs)
