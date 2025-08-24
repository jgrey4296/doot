#!/usr/bin/env python3
"""


"""
# ruff: noqa:

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import re
import time
import types
import collections
import contextlib
import hashlib
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref
import atexit # for @atexit.register
import faulthandler
from importlib.resources import files
from importlib.metadata import version
# ##-- end stdlib imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload
from jgdv.structs.chainguard import ChainGuard

if TYPE_CHECKING:
    import pathlib as pl
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from importlib.resources.abc import Traversable
    from jgdv import Maybe, VerStr

    type Loadable = pl.Path | Traversable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
__version__ : Final[str] = version("doot")

# -- data
data_path                  = files("doot.__data")
constants_file : Loadable  = data_path.joinpath("constants.toml")
aliases_file   : Loadable  = data_path.joinpath("aliases.toml")
template_path  : Loadable  = files("doot.__data.templates")

# -- Can't be in doot.constants, because that isn't loaded yet
CONSTANT_PREFIX    : Final[str]              = "doot.constants"
ALIAS_PREFIX       : Final[str]              = "doot.aliases"
TOOL_PREFIX        : Final[str]              = "tool.doot"
DOOT_TOML          : Final[str]              = "doot.toml"
PYPROJ_TOML        : Final[str]              = "pyproject.toml"
DEFAULT_FILENAMES  : Final[tuple[str, ...]]  = (DOOT_TOML, PYPROJ_TOML)

fail_prefix        : Final[str]              = "!!!"
GLOBAL_STATE_KEY   : Final[str]              = "global"
LASTERR            : Final[str]              = "doot.lasterror"

##--|
class ExitCodes(enum.IntEnum):
    SUCCESS          = 0
    UNKNOWN_FAIL     = -1
    NOT_SETUP        = -2
    EARLY            = -3
    MISSING_CONFIG   = -4
    BAD_CONFIG       = -5
    BAD_CMD          = -6
    TASK_FAIL        = -7
    BAD_STATE        = -8
    BAD_STRUCT       = -9
    TRACKING_FAIL    = -10
    BACKEND_FAIL     = -11
    FRONTEND_FAIL    = -12
    DOOT_FAIL        = -13
    NOT_IMPLEMENTED  = -14
    IMPORT_FAIL      = -15
    PYTHON_FAIL      = -16

    INITIAL          = -99
