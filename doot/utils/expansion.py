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
# from dataclasses import InitVar, dataclass, field
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

from collections import UserString
import string
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.constants import KEY_PATTERN, MAX_KEY_EXPANSIONS

from doot._structs.key import DootFormatter, DootKey

PATTERN : Final[re.Pattern] = re.compile("{(.+?)}")

def to_key(key, spec, state) -> DootKey:
    return DootKey.make(key)

def to_any(key, spec, state, type_=Any) -> Any:
    key = DootKey.make(key)
    return key.to_type(spec, state, type_=type_)

def to_str(key, spec, state, rec=False) -> str:
    match DootKey.make(key):
        case DootKey() as k:
            return k.expand(spec, state, rec=rec)
        case str() as k:
            fmt = DootFormatter()
            return fmt.format(k, _spec=spec, _state=state, _rec=rec)

def to_path(key, spec, state) -> pl.Path:
    match key:
        case str():
            key = DootKey.make(key)
            return key.to_path(spec, state)
        case pl.Path():
            fmt = DootFormatter()
            return fmt.format(key, _spec=spec, _state=state, _as_path=True)

def expand_path_part(part:str, data:TomlGuard) -> str:
    """ Given a part of a path, expand any keys found"""
    count         = 0
    expanded_part = part
    # Expand any keys found in each part
    while m := re.search(KEY_PATTERN, expanded_part):
        if count > MAX_KEY_EXPANSIONS:
            raise doot.errors.DootLocationExpansionError("Root key: %s, last expansion: %s", part, expanded_part)
        count += 1
        wr_key  = m[0]
        if m[1] not in data:
            raise doot.errors.DootLocationError("Missing Location Key: %s", part)
        sub_val       = data[m[1]]
        expanded_part = re.sub(wr_key, sub_val, expanded_part)

    return expanded_part
