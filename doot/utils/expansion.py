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
PATTERN = re.compile("{(.+?)}")

def expand_key(s, spec, task_state, as_path=False):
    """
      Expansion, with a level of indirection
      expand_key("aKey", spec("aKey": "blah")...) -> expand_str("{blah}"..)
    """
    expanded_key = expand_str(s, spec, task_state, as_key=True)
    if as_path:
        return expand_str(expanded_key, spec, task_state, as_path=True)

    return expand_to_obj(expanded_key, spec, task_state)

def expand_str(s, spec=None, task_state=None, as_path=False, as_key=False):
    """
    expand {keywords} in a string that are in the spec.kwargs or task_state
    but don't complain about other keywords, that found in doot.locs

    if as_path, then doot.locs expands those kwargs last, returning a path
    """
    match s:
        case pl.Path():
            logging.warning("Tried to expand_str a path: %s", s)
            return s
        case list():
            logging.debug("Tried to expand_str a list, sub-expanding: %s", s)
            return [expand_str(x, spec, task_state, as_path=as_path, as_key=as_key) for x in s]
        case set():
            logging.debug("Tried to expand_str a set, sub-expanding: %s", s)
            return set(expand_str(x, spec, task_state, as_path=as_path, as_key=as_key) for x in s)

    curr       = s
    task_state = task_state or {}
    kwargs     = spec.kwargs if spec is not None else {}
    matched    = set(PATTERN.findall(curr))
    cast_to_path = False
    for x in matched:
        replacement = task_state.get(x, None) or kwargs.get(x, None)
        if isinstance(replacement, str) and PATTERN.search(replacement):
            replacement = expand_str(replacement, spec, task_state)

        if x in doot.locs:
            cast_to_path = True

        match replacement:
            case None:
                pass
            case list():
                val = " ".join(str(x) for x in replacement)
                curr = re.sub(f"{{{x}}}", val, curr)
            case pl.Path():
                curr = re.sub(f"{{{x}}}", str(replacement), curr)
            case str():
                curr = re.sub(f"{{{x}}}", replacement, curr)
            case _:
                curr = re.sub(f"{{{x}}}", str(replacement), curr)

    if as_path or cast_to_path:
        return doot.locs[curr]
    if as_key:
        return "{"+curr+"}"

    return curr


def expand_set(s, spec=None, task_state=None, as_path=False) -> list:
    """
    expand {keywords} in a string that are in the spec.kwargs or task_state
    but don't complain about other keywords, that found in doot.locs

    if as_path, then doot.locs expands those kwargs last, returning a path
    """
    match s:
        case pl.Path():
            logging.warning("Tried to expand_str a path: %s", s)
            return set([s])
        case list() | set():
            logging.debug("Tried to expand_str a list, sub-expanding: %s", s)
            result = set()
            for x in s:
                result.update(expand_set(x, spec, task_state, as_path=as_path))
            return result

    curr         = s
    task_state   = task_state or {}
    kwargs       = spec.kwargs if spec is not None else {}
    matched      = set(PATTERN.findall(curr))
    cast_to_path = False
    result       = set()
    if not bool(matched):
        return set([s])

    for x in matched:
        match x:
            case None:
                pass
            case list() | set():
                logging.debug("Adding: %s", x)
                result.update(x)
            case str() if x in spec.kwargs or x in task_state:
                match expand_to_obj("{"+x+"}", spec, task_state):
                    case list() | set() as y:
                        result.update(y)
                    case _ as y:
                        result.add(y)
            case _:
                logging.debug("Adding: %s", x)
                result.add(x)

    if as_path:
        return set(doot.locs[x] for x in result)
    else:
        return result

def expand_to_obj(s, spec=None, task_state=None):
    """
    expand {keywords} in a string that are in the spec.kwargs or task_state
    but don't complain about other keywords, that found in doot.locs

    if as_path, then doot.locs expands those kwargs last, returning a path
    """
    if not isinstance(s, str):
        return s

    curr       = s
    task_state = task_state or {}
    kwargs     = spec.kwargs if spec is not None else {}
    matched    = PATTERN.findall(curr)
    if not bool(matched):
        raise KeyError("No Key Matched", s)
    if len(matched) > 1:
        raise KeyError("Can only expand to a single obj", s)

    replacement = task_state.get(matched[0], None) or kwargs.get(matched[0], None)

    if replacement is None:
        raise KeyError("No Key Found in State", matched)

    return replacement



"""


"""


def expand_path_part(part:str, data:TomlGuard):
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
