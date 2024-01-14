#!/usr/bin/env python3
"""
A function to select an appropriate plugin by passed in name or names

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

import importlib
from importlib.metadata import EntryPoint
from doot.structs import DootCodeReference
import doot.errors

def plugin_selector(plugins:TomlGuard, *, target="default", fallback=None) -> type:
    """ Selects and loads plugins from a tomlguard, based on a target,
    with an available fallback constructor """
    logging.debug("Selecting plugin for target: %s", target)

    if target != "default":
        try:
            name = DootCodeReference.from_str(target)
            return name.try_import()
        except ImportError as err:
            # raise doot.errors.DootInvalidConfig("Import Failed: %s : %s", target, err.msg) from err
            pass
        except (AttributeError, KeyError) as err:
            # raise doot.errors.DootInvalidConfig("Import Failed: Module has missing attritbue/key: %s", target) from err
            pass

    match plugins:
        case x if not isinstance(x, list):
            return x
        case [] if fallback is not None:
            return fallback()
        case []:
            raise ValueError("No Available Plugin, and no fallback constructor")
        case [EntryPoint() as l]: # if theres only one, use that
            return l.load()
        case [EntryPoint() as l, *_] if target == "default": # If the preference is the default, use the first
            return l.load()
        case [*_] as loaders: # Otherwise, use the loader that matches the preferred's name
            matching = [x for x in loaders if x.name == target]
            if bool(matching):
                return matching[0].load()
