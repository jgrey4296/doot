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

import doot
PATTERN = re.compile("{(.+?)}")

def expand_str(s, spec=None, task_state=None, as_path=False):
    """
    expand {keywords} in a string that are in the spec.kwargs or task_state
    but don't complain about other keywords, which can be expanded by doot.locs
    """
    match s:
        case pl.Path():
            return s
        case set():
            return " ".join([expand_str(x, spec, task_state) for x in s])

    curr       = s
    task_state = task_state or {}
    kwargs     = spec.kwargs if spec is not None else {}
    matched    = set(PATTERN.findall(curr))
    cast_to_path = False
    for x in matched:
        replacement = task_state.get(x, None) or kwargs.get(x, None)

        if x in doot.locs:
            cast_to_path = True

        match replacement:
            case None:
                pass
            case set():
                val = " ".join(str(x) for x in replacement)
                curr = re.sub(f"{{{x}}}", val, curr)
            case pl.Path():
                curr = re.sub(f"{{{x}}}", str(replacement), curr)
            case _:
                curr = re.sub(f"{{{x}}}", replacement, curr)

    if as_path or cast_to_path:
        return doot.locs[curr]
    else:
        return curr





"""


"""
