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

import string
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.constants import KEY_PATTERN, MAX_KEY_EXPANSIONS

PATTERN : Final[re.Pattern] = re.compile("{(.+?)}")
Key     : TypeAlias = str

def to_any(key, spec, state, indirect=False) -> Any:
    if indirect:
        key = "{"+key+"}"

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

def to_str(key:Key, spec, state, indirect=False) -> str:
    if indirect:
        key = "{" + key + "}"

    state             = state or {}
    kwargs            = spec.kwargs if spec is not None else {}
    expanded : str    = key
    for matched in PATTERN.finditer(expanded):
        replacement = state.get(matched[1], None) or kwargs.get(matched[1], None)

        match replacement:
            case None:
                continue
            case list():
                raise TypeError("Key Replacement is a list", key, replacement)
            case pl.Path():
                return replacement
            case str():
                try:
                    expanded = re.sub(matched[0], replacement, expanded, count=1)
                except re.error as err:
                    expanded = expanded[:matched.start(0)] + replacement + expanded[matched.end(0):]
            case _:
                raise TypeError("Key Replacement isnt a str", key, replacement)

    return expanded

def to_path(key, spec, state, indirect=False) -> pl.Path:
    expanded  = to_str(key, spec, state, indirect=indirect)
    flattened = to_str(expanded, spec, state)
    return doot.locs[flattened]


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

class DootFormatter(string.Formatter):

    def format(self, fmt, /, *args, indirect=False, as_path=False, **kwargs) -> str:
        self._depth = 0
        if indirect:
            fmt = "{"+fmt+"}"
        result = self.vformat(fmt, args, kwargs)
        if as_path:
            return doot.locs[result]

        return result

    def get_value(self, key, args, kwargs):
        logging.debug("Expanding: %s", key)
        if isinstance(key, int):
            return args[key]

        state             = kwargs.get('state')
        spec              = kwargs.get('spec').kwargs
        replacement       = state.get(key, None) or spec.get(key, None)
        logging.debug("Expanded to: %s", replacement)
        if replacement and kwargs.get("recursive", False) and self._depth < MAX_KEY_EXPANSIONS:
            self._depth += 1
            return self.vformat(replacement, args, kwargs)

        return replacement or "{"+key+"}"
