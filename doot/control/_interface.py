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
from typing import no_type_check, final
import pathlib as pl

if TYPE_CHECKING:
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from logging import Logger

    from jgdv import Maybe
    from jgdv.cli import ParseMachine
    from jgdv.cli._interface import ParseReport_d
    from jgdv.structs.chainguard import ChainGuard
    from jgdv.logging import JGDVLogConfig
    from jgdv.structs.locator import JGDVLocator
    from doot.cmd._interface import Command_p
    from doot.errors import DootError

    from .._interface import Loadable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
LOG_PREFIX  : Final[str]  = "----"
PYPROJ      : Final[str]  = "pyproject.toml"
ROOT_ELEM   : Final[str]  = "doot"
# Body:

@runtime_checkable
class Overlord_p(Protocol):
    """
    protocol for the doot accesspoint,
    used for setting up and using Doot programmatically
    """

    def setup(self, *, targets:Maybe[list[Loadable]]=None, prefix:str) -> None: ...

    def load(self) -> None: ...

    def load_reporter(self, target:str="default") -> None: ...

    def verify_config_version(self, ver:Maybe[str], sources:str|pl.Path, *, override:Maybe[str]=None) -> None: ...

    def update_aliases(self, *, data:dict|ChainGuard) -> None: ...

    def update_cmd_args(self, data:ParseReport_d|dict) -> None: ...

    def update_global_task_state(self, data:ChainGuard, *, source:Maybe[str]=None) -> None: ...

    def update_import_path(self, *paths:pl.Path) -> None: ...

class Overlord_i(Overlord_p, Protocol):
    """
    protocol for the doot accesspoint,
    used for setting up and using Doot programmatically
    """
    __version__         : str
    config              : ChainGuard
    constants           : ChainGuard
    aliases             : ChainGuard
    cmd_aliases         : ChainGuard
    args                : ChainGuard
    locs                : JGDVLocator
    configs_loaded_from : list[str|pl.Path]
    global_task_state   : dict
    path_ext            : list[str]
    is_setup            : bool
    loaded_plugins      : ChainGuard
    loaded_cmds         : ChainGuard
    loaded_tasks        : ChainGuard

@runtime_checkable
class Main_p(Protocol):
    """
    protocol for doot as a main program
    """

    def __init__(self, *, args:Maybe[list]=None) -> None: ...

    def __call__(self) -> None: ...

    @property
    def name(self) -> str: ...
    def handle_cli_args(self) -> Maybe[int]: ...

    def help(self) -> str: ...

    def setup_logging(self) -> None: ...

class Main_i(Main_p, Protocol):
    """
    protocol for doot as a main program
    """

    result_code  : int
    prog_name    : str
    raw_args     : list[str]
    current_cmd  : Maybe[Command_p]
    parser       : Maybe[ParseMachine]
    log_config   : JGDVLogConfig
