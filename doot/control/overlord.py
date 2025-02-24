#!/usr/bin/env python3
"""

"""
# ruff: noqa: W291, ARG002, ANN001

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import atexit#  for @atexit.register
import collections
import contextlib
import datetime
import enum
import faulthandler
import functools as ftz
import hashlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import sys
import time
import types
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
from packaging.specifiers import SpecifierSet
from jgdv import JGDVError, Mixin, Proto
from jgdv.structs.chainguard import ChainGuard
from jgdv.logging import JGDVLogConfig
from jgdv.structs.dkey import DKey
from jgdv.structs.locator import JGDVLocator

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot._interface as API#  noqa: N812
import doot.errors
# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from collections import defaultdict
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload
from doot._abstract import (Command_p, Overlord_p)

if TYPE_CHECKING:
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from doot._abstract.loader import Loader_p
    from jgdv import Maybe

    type Logger                            = logmod.Logger
    type DootError                         = doot.errors.DootError

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:

# Body:

class Startup_m:

    def setup(self, *, targets:Maybe[list[pl.Path]|False]=None, prefix:Maybe[str]=API.TOOL_PREFIX) -> None: # noqa: PLR0912
        """
        The core requirement to call before any other doot code is run.
        loads the config files, so everything else can retrieve values when imported.

        `prefix` removes a prefix from the loaded data.
        eg: 'tool.doot' for if putting doot settings in a pyproject.toml

        targets=False is for loading nothing, for testing
        """
        match targets:
            case False:
                targets :list[pl.Path] = []
            case list() if bool(targets) and all([isinstance(x, pl.Path) for x in targets]):
                targets : list[pl.Path] = [pl.Path(x) for x in targets]
            case list() if bool(targets):
                raise TypeError("Doot Config Targets should be pathlib.Path's", targets)
            case _:
                targets : list[pl.Path] = [pl.Path(x) for x in self.constants.paths.DEFAULT_LOAD_TARGETS]

        logging.log(0, "Loading Doot Config, version: %s targets: %s", API.__version__, targets)
        if self.is_setup:
            logging.warning("doot.setup called even though doot is already set up")

        # Load config Files
        match [x for x in targets if x.exists()]:
            case [] if bool(targets):
                raise doot.errors.MissingConfigError("No Doot data found")
            case []:
                 existing_targets = []
            case [*xs]:
                existing_targets = xs
            case x:
                raise TypeError(type(x))

        try:
            config = ChainGuard.load(*existing_targets)
        except OSError as err:
            raise doot.errors.InvalidConfigError(existing_targets, *err.args) from err
        else:
            if existing_targets == [pl.Path("pyproject.toml")] and "doot" not in config:
                raise doot.errors.MissingConfigError("Pyproject has no doot config")
        finally:
            self.configs_loaded_from   += existing_targets
            self.config = config.remove_prefix(prefix)
            if bool(existing_targets):
                self.verify_config_version(self.config.on_fail(None).startup.doot_version(), source=targets)

        ##--|
        # Config Loaded, use it
        self._setup_logging()
        self._load_constants()
        self._load_aliases()
        self._load_locations()
        self._update_import_path()
        self._set_command_aliases()

        # add global task state
        self.update_global_task_state(self.config, source="doot.toml")
        DKey.add_sources(self.global_task_state)

    def _load_constants(self) -> None:
        """ Load the override constants if the loaded base config specifies one
        Modifies the global `doot.constants`
        """
        match self.config.on_fail(None).startup.constants_file(wrapper=pl.Path):
            case None:
                pass
            case pl.Path() as const_file if const_file.exists():
                self.setup_l.trace("Loading Constants")
                base_data = ChainGuard.load(const_file)
                self.verify_config_version(base_data.on_fail(None).doot_version(), source=const_file)
                self.constants = base_data.remove_prefix(API.CONSTANT_PREFIX)

    def _load_aliases(self, *, data:Maybe[dict|ChainGuard]=None, force:bool=False) -> None:
        """ Load plugin aliases.
        if given the kwarg `data`, will *append* to the aliases
        Modifies the global `doot.aliases`
        """
        if not bool(self.aliases):
            match self.config.on_failj(API.aliases_file).startup.aliases_file(wrapper=pl.Path):
                case _ if bool(self.aliases) and not force:
                    base_data = {}
                    pass
                case pl.Path() as source if source.exists():
                    self.setup_l.trace("Loading Aliases: %s", source)
                    base_data = ChainGuard.load(source)
                    self.verify_config_version(base_data.on_fail(None).doot_version(), source=source)
                    base_data = base_data.remove_prefix(API.ALIAS_PREFIX)
                case source:
                    self.setup_l.trace("Alias File Not Found: %s", source)
                    base_data = {}

            # Flatten the lists
            flat = {}
            for key,val in base_data.items():
                flat[key] = {k:v for x in val for k,v in x.items()}

            # Then override with config specified plugin items:
            for key,val in self.config.on_fail({}).startup.plugins().items():
                flat[key].update(dict(val))

            self.aliases = ChainGuard(flat)

        match data:
            case None:
                pass
            case _ if bool(data):
                self.setup_l.trace("Updating Aliases")
                base = defaultdict(dict)
                base.update(dict(self.aliases._table()))
                for key,eps in data.items():
                    update = {x.name:x.value for x in eps}
                    base[key].update(update)

                self.aliases = ChainGuard(base)

    def _load_locations(self) -> None:
        """ Load and update the JGDVLocator db
        Modifies the global `doot.locs`
        """
        self.setup_l.trace("Loading Locations")
        self.locs   = JGDVLocator(pl.Path.cwd())
        # Load Initial locations
        for loc in self.config.on_fail([]).locations():
            try:
                for name in loc.keys():
                    self.setup_l.trace("+ %s", name)
                    self.locs.update(loc, strict=False)
            except (JGDVError, ValueError) as err:
                self.setup_l.error("Location Loading Failed: %s (%s)", loc, err)

    def _update_import_path(self) -> None:
        """ Add locations to the python path for task local code importing
        Modifies the global `sys.path`
        """
        self.setup_l.trace("Updating Import Path")
        task_sources = self.config.on_fail([self.locs[".tasks"]], list).startup.sources.tasks(wrapper=lambda x: [self.locs[y] for y in x])
        task_code    = self.config.on_fail([self.locs[".tasks"]], list).startup.sources.code(wrapper=lambda x: [self.locs[y] for y in x])
        for source in set(task_sources + task_code):
            match source:
                case None:
                    pass
                case x if x.exists() and x.is_dir():
                    self.setup_l.trace("+ %s", source)
                    sys.path.append(str(source))

    def _set_command_aliases(self) -> None:
        """ Read settings.commands.* and register aliases """
        self.setup_l.trace("Setting Command Aliases")
        registered = {}
        for name,details in self.config.on_fail({}).settings.commands().items():
            for alias, args in details.on_fail({}, non_root=True).aliases().items():
                self.setup_l.trace("- %s -> %s", name, alias)
                registered[alias] = [name, *args]
        else:
            self.cmd_aliases = ChainGuard(registered)
            self.setup_l.trace("Finished Command Aliases")

class Logging_m:

    def subprinter(self, name:Maybe[str]=None, *, prefix=None) -> Logger:
        """ Get a sub-printer at position `name`.
        Names are registered using JGDV.logging.LogConfig
        """
        try:
            return self.log_config.self.subprinter(name, prefix=prefix)
        except ValueError as err:
            raise doot.errors.ConfigError("Invalid Subprinter", name) from err

    def _setup_logging(self) -> None:
        self.log_config.setup(self.config)
        self.overlord_l      = self.subprinter("overlord")
        self.header_l        = self.subprinter("header")
        self.setup_l         = self.subprinter("setup")
        self.help_l          = self.subprinter("help")
        self.self.shutdown_l = self.subprinter("shutdown")
        self.fail_l          = self.subprinter("fail", prefix=API.fail_prefix)

class WorkflowArgs_m:

    def set_args(self, data:ChainGuard):
        self.args = data

##--|

@Proto(Overlord_p)
@Mixin(Startup_m, Logging_m)
class DootOverlord:
    """
    TODO make singleton
    The main control point of Doot
    The setup logic of doot.

    As Doot uses loaded config data throughout, using the doot.config.on_fail... pattern,
    the top-level package 'doot', uses a module getattr to offload attribute access to this class.

    """

    def __init__(self):
        self.config                                   = ChainGuard()
        self.constants                                = ChainGuard.load(API.constants_file).remove_prefix(API.CONSTANT_PREFIX)
        self.aliases                                  = ChainGuard()
        self.cmd_aliases                              = ChainGuard()
        self.args                                     = ChainGuard() # parsed arg access
        self.log_config                               = JGDVLogConfig(self.constants.on_fail(None).printer.PRINTER_CHILDREN())
        self.configs_loaded_from : list[str]          = []
        self.global_task_state   : dict               = {}
        self.locs                : Maybe[JGDVLocator] = None
        self.is_setup                                 = False

    def verify_config_version(self, ver:Maybe[str], source:str|pl.Path) -> None:
        "Ensure the config file is compatible with doot"
        doot_ver = SpecifierSet(f"~={API.__version__}")
        match ver:
            case str() as x if x in doot_ver:
                return
            case str() as x:
                raise doot.errors.VersionMismatchError("Config File is incompatible with this version of doot (%s) : %s : %s", API.__version__, x, source)
            case _:
                raise doot.errors.VersionMismatchError("No Doot Version Found in config file: %s", source)

    def update_global_task_state(self, data:ChainGuard, *, source:Maybe[str]=None) -> None:
        """ Try to Update the shared global state.
        Will try to get data[doot._interface.GLOBAL_STATE_KEY] data and add it to the global task state

        toml in [[state]] segments is merged here
        """
        assert(source is not None)
        self.setup_l = self.subprinter("setup")
        self.setup_l.trace("Updating Global State from: %s", source)
        if not isinstance(data, dict|ChainGuard):
            raise doot.errors.GlobalStateMismatch("Not a dict", data)

        match data.on_fail([])[API.GLOBAL_STATE_KEY]():
            case []:
                pass
            case [*xs]:
                updates = xs
            case dict() as x:
                updates = [x]
            case x:
                raise TypeError(type(x))

        for up in updates:
            for x,y in up.items():
                if x not in self.global_task_state:
                    self.global_task_state[x] = y
                elif self.global_task_state[x] != y:
                    raise doot.errors.GlobalStateMismatch(x, y, source)

    def _null_setup(self) -> None:
        """
        Doesn't load anything but constants,
        Used for initialising Doot when testing.
        """
        self.setup(False)  # noqa: FBT003
