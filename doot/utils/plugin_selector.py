#!/usr/bin/env python3
"""
A function to select an appropriate plugin by passed in name or names


"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
# import abc
import datetime
import enum
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
from importlib.metadata import EntryPoint
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.strang import CodeReference
from jgdv.structs.chainguard import ChainGuard
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot.errors

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

def plugin_selector(plugins:ChainGuard, *, target="default", fallback=None) -> type:
    """ Selects and loads plugins from a chainguard , based on a target,
    with an available fallback constructor """
    logging.debug("Selecting plugin for target: %s", target)

    match target:
        case "default":
            pass
        case x:
            try:
                name = CodeReference.build(target)
                return name.try_import()
            except ImportError as err:
                pass
            except (AttributeError, KeyError) as err:
                pass

    match plugins:
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
        case type():
            return x
        case _:
            raise TypeError("Unknown type passed to plugin selector", plugins)
