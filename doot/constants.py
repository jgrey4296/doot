##-- std imports
from __future__ import annotations

# import datetime
# import enum
import pathlib as pl
import types
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from importlib import resources
import re
from tomlguard import TomlGuard
##-- end std imports

from doot._default_plugins import *

##-- plugin names and loaders
PLUGIN_TOML_PREFIX         : Final = "doot.plugins" # (project.entry-points."doot.plugins")
FRONTEND_PLUGIN_TYPES      : Final = ['command', 'reporter', 'report-line']
BACKEND_PLUGIN_TYPES       : Final = [
    'database', 'tracker', 'runner',
    'command-loader', 'task-loader',
    'parser', 'action', "task", "mixins"
    ]

DEFAULT_COMMAND_LOADER_KEY  : Final[str] =  "command-loader"

DEFAULT_TASK_LOADER_KEY     : Final[str] =  "task-loader"

DEFAULT_PLUGIN_LOADER_KEY   : Final[str] =  "plugin-loader"
##-- end plugin names and loaders

##-- path and file names
TEMPLATE_PATH         : Final[pl.Path]       =  resources.files("doot.__templates")
TOML_TEMPLATE         : Final[pl.Path]       =  TEMPLATE_PATH / "basic_toml"

DEFAULT_LOAD_TARGETS  : Final[list[pl.Path]] =  [pl.Path(x) for x in ["doot.toml", "pyproject.toml", "Cargo.toml", "./.cargo/config.toml"]]

DEFAULT_STUB_TASK_NAME : Final[str] = "stub::stub"

##-- end path and file names

KEY_PATTERN                                       = re.compile("{(.+?)}")
MAX_KEY_EXPANSIONS                                = 10

TASK_SEP                : Final[str]              = "::"
IMPORT_SEP              : Final[str]              = ":"
SUBTASKED_HEAD          : Final[str]              = "$head$"
CONFLICTED_ADD          : Final[str]              = "$conflict$"
INTERNAL_TASK_PREFIX    : Final[str]              = "_"
FILE_DEP_PREFIX         : Final[str]              = "file:>"
PARAM_ASSIGN_PREFIX     : Final[str]              = "--"

DEFAULT_CLI_CMD         : Final[str]              = "run"

DEFAULT_TASK_PREFIX     : Final[str]              = "task_"

DEFAULT_TASK_GROUP      : Final[str]              = "default"

ANNOUNCE_EXIT           : Final[bool]             = False

ANNOUNCE_VOICE          : Final[str]              = "Moira"

PRINTER_NAME            : Final[str]              = "doot._printer"

PRINT_LOCATIONS         : Final[set]              = {"head", "build", "action", "sleep", "execute" }

DEFAULT_HEAD_LEVEL      : Final[str]              = "INFO"

DEFAULT_BUILD_LEVEL     : Final[str]              = "WARN"

DEFAULT_ACTION_LEVEL    : Final[str]              = "INFO"

DEFAULT_SLEEP_LEVEL     : Final[str]              = "WARN"

DEFAULT_EXECUTE_LEVEL   : Final[str]              = "INFO"

NON_DEFAULT_KEY         : Final[str]              = "_non_default"
