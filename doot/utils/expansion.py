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

from tomlguard import TomlGuard
import doot
import doot.errors
from doot.constants import KEY_PATTERN, MAX_KEY_EXPANSIONS

PATTERN : Final[re.Pattern] = re.compile("{(.+?)}")
Key     : TypeAlias = str

def has_expansions(key) -> bool:
    return bool(PATTERN.search(key))

def indirect_key(key:str, spec:DootActionSpec, state:dict) -> Key:
    """
      retrieve a key 'x', {x:"blah"} (without it being wrapped in {}),
      and return it as an expansion key '{blah}'
    """
    state        = state or {}
    kwargs       = spec.kwargs if spec is not None else {}

    replacement = state.get(key, None) or kwargs.get(key, None)

    if replacement is None:
        return "{"+key+"}"

    if not isinstance(replacement, str):
        raise TypeError("Indirect key isn't a string", key, replacement)

    return "{"+replacement+"}"

def to_str(key:Key, spec, state, indirect=False) -> str:
    if indirect:
        key = indirect_key(key, spec, state)

    state             = state or {}
    kwargs            = spec.kwargs if spec is not None else {}
    expanded : str    = key
    matched           = set(PATTERN.findall(key))
    for x in matched:
        replacement = state.get(x, None) or kwargs.get(x, None)

        match replacement:
            case None:
                continue
            case str() if PATTERN.search(replacement):
                raise TypeError("Key Replacement is a key as well", key, replacement)
            case list():
                raise TypeError("Key Replacement is a list", key, replacement)
            case pl.Path():
                raise TypeError("Key Replacement is a path", key, replacement)
            case str():
                expanded = re.sub(f"{{{x}}}", replacement, expanded)
            case _:
                raise TypeError("Key Replacement isnt a str", key, replacement)

    return expanded


def to_path(key, spec, state, indirect=False) -> pl.Path:
    if indirect:
        key = indirect_key(key, spec, state)
    expanded = to_str(key, spec, state)
    return doot.locs[expanded]


def to_any(key, spec, state, indirect=False) -> Any:
    if indirect:
        key = indirect_key(key, spec, state)

    state             = state or {}
    kwargs            = spec.kwargs if spec is not None else {}
    expanded : str    = key
    matched           = list(PATTERN.findall(key))
    if not bool(matched):
        return key
    if len(matched) > 1:
        raise TypeError("Expansion to anything can't handle multiple keys", key)

    target = matched.pop()
    replacement = state.get(target, None) or kwargs.get(target, None)

    match replacement:
        case None:
            return key
        case _:
            return replacement


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
