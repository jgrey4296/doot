#!/usr/bin/env python3
"""
Utility actions, such as a debugger

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
printer = logmod.getLogger("doot._printer")

import bdb
import doot
import doot.errors

def action_debugger(spec, state):
    def pstate():
        printer.info("Printing State:")
        printer.info(state)

    def pspec():
        printer.info("Printing Spec:")
        printer.info(spec)

    printer.info("* Entering breakpoint *")
    printer.info("* Call pspec() and pstate() to inspect the spec and state *")
    breakpoint()

    return None

def typecheck(spec, state):
    for key,target_type in spec.kwargs:
        try:
            value = state[key]
            value_type = type(value)
            fullname = "{}:{}".format(value_type.__module__, value_type.__name__)
            if target_type != fullname:
                raise doot.errors.DootActionStateError("Type Error: state.%s : %s != %s", key, fullname, target_type)

            printer.debug("Type Matches: state.%s : %s", key, target_type)

        except (AttributeError, KeyError):
            raise doot.errors.DootActionStateError("State key missing: %s", key)
