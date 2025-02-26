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
import pathlib as pl
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
# ##-- end stdlib imports

import doot

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
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Config Vars:
skip_default_plugins : Final[bool]          = doot.config.on_fail(False).startup.skip_default_plugins()
skip_plugin_search   : Final[bool]          = doot.config.on_fail(False).startup.skip_plugin_search()
env_plugins          : Final[dict]          = doot.config.on_fail({}).startup.plugins(wrapper=dict)
task_sources         : Final[pl.Path]       = doot.config.on_fail([doot.locs.Current[".tasks"]], list).startup.sources.tasks.sources(wrapper=lambda x: [doot.locs[y] for y in x])
allow_overloads      : Final[bool]          = doot.config.on_fail(False, bool).allow_overloads()

# Constants:
## The plugin types to search for:
frontend_plugins     : Final[list]          = doot.constants.entrypoints.FRONTEND_PLUGIN_TYPES
backend_plugins      : Final[list]          = doot.constants.entrypoints.BACKEND_PLUGIN_TYPES
plugin_types         : Final[set]           = set(frontend_plugins + backend_plugins)

cmd_loader_key       : Final[str]           = doot.constants.entrypoints.DEFAULT_COMMAND_LOADER_KEY
task_loader_key      : Final[str]           = doot.constants.entrypoints.DEFAULT_TASK_LOADER_KEY
PLUGIN_PREFIX        : Final[str]           = doot.constants.entrypoints.PLUGIN_TOML_PREFIX
DEFAULT_CMD_LOADER   : Final[str]           = doot.constants.entrypoints.DEFAULT_COMMAND_LOADER
DEFAULT_TASK_LOADER  : Final[str]           = doot.constants.entrypoints.DEFAULT_TASK_LOADER
DEFAULT_TASK_GROUP   : Final[str]           = doot.constants.names.DEFAULT_TASK_GROUP
IMPORT_SEP           : Final[str]           = doot.constants.patterns.IMPORT_SEP

# Other
TASK_STRING          : Final[str]           = "task_"
prefix_len           : Final[int]           = len(TASK_STRING)
TOML_SUFFIX          : Final[str]           = ".toml"


# Body:
