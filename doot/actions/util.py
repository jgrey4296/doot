#!/usr/bin/env python3
"""
Utility actions, such as a debugger


"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import bdb
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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.structs import DKey

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

def action_debugger(spec, state):
    """ A Simple entry function for debugging spec and state """
    def pstate():
        doot.report.trace("Printing State:")
        doot.report.trace(state)

    def pspec():
        doot.report.trace("Printing Spec:")
        doot.report.trace(spec)

    doot.report.trace("* Entering breakpoint *")
    doot.report.trace("* Call pspec() and pstate() to inspect the spec and state *")

    breakpoint()

    return None

def typecheck(spec, state):
    """ a simple action to check the expansion of certain keys """
    for key,target_type in spec.kwargs:
        try:
            d_key      = DKey(key)
            value      = d_key.expand(state)
            value_type = type(value)
            fullname   = value_type.__qualname__
            if target_type != fullname:
                raise doot.errors.KeyExpansionError("Type Error: state.%s : %s != %s", key, fullname, target_type)

            doot.report.detail("Type Matches: state.%s : %s", key, target_type)

        except (AttributeError, KeyError):
            raise doot.errors.KeyAccessError("State key missing: %s", key)
