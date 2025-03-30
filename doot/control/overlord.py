#!/usr/bin/env python3
"""

"""
# mypy: disable-error-code="attr-defined"
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
from packaging.version import Version
from jgdv import JGDVError, Mixin, Proto
from jgdv.structs.metalord.singleton import MLSingleton
from jgdv.structs.chainguard import ChainGuard
from jgdv.logging import JGDVLogConfig
from jgdv.structs.dkey import DKey
from jgdv.structs.locator import JGDVLocator

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot._interface as API#  noqa: N812
import doot.errors as DErr  # noqa: N812
from doot.reporters import NullReporter
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
from doot.reporters._interface import GeneralReporter_p as Reporter_p

if TYPE_CHECKING:
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from jgdv import Maybe
    from doot._abstract.loader import Loader_p

    type Logger                            = logmod.Logger
    type DootError                         = DErr.DootError

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
PYPROJ    : Final[pl.Path] = pl.Path("pyproject.toml")
ROOT_ELEM : Final[str]     = "doot"
# Body:

class Startup_m:
    """
    Overlord startup/setup methods
    """
    is_setup            : bool
    global_task_state   : dict
    aliases             : ChainGuard

    def null_setup(self) -> None:
        """
        Doesn't load anything but constants,
        Used for initialising Doot when testing.
        Doesn't set the is_setup flag.
        """
        if self.is_setup:
            return

        self._load_constants()
        self._load_aliases()

    def setup(self, *, targets:Maybe[list[pl.Path]]=None, prefix:Maybe[str]=API.TOOL_PREFIX) -> None:
        """
        The core requirement to call before any other doot code is run.
        loads the config files, so everything else can retrieve values when imported.

        `prefix` removes a prefix from the loaded data.
        eg: 'tool.doot' for if putting doot settings in a pyproject.toml

        targets=False is for loading nothing, for testing
        """
        if self.is_setup:
            self.report.user("doot.setup called even though doot is already set up") # type: ignore

        self._load_config(targets, prefix)
        self._setup_logging() # type: ignore
        self._load_constants()
        self._load_aliases()
        self._load_locations()
        self._update_import_path()

        # add global task state as a DKey expansion source
        DKey.add_sources(self.global_task_state)
        self.is_setup = True

    def _load_config(self, targets:Maybe[list[pl.Path]], prefix:Maybe[str]) -> None:
        """ Load a specified config, or one of the defaults if it exists """
        match targets:
            case list() if bool(targets) and all([isinstance(x, pl.Path) for x in targets]):
                targets : list[pl.Path] = [pl.Path(x) for x in targets] # type: ignore
            case list() if bool(targets):
                raise TypeError("Doot Config Targets should be pathlib.Path's", targets)
            case None | []:
                targets : list[pl.Path] = [pl.Path(x) for x in self.constants.paths.DEFAULT_LOAD_TARGETS] # type: ignore

        logging.log(0, "Loading Doot Config, version: %s targets: %s", API.__version__, targets)

        assert(isinstance(targets, list))
        match [x for x in targets if x.exists()]:
            case [] if bool(targets):
                raise DErr.MissingConfigError("No Doot data found")
            case []:
                existing_targets = []
            case [*xs]:
                existing_targets = xs
            case x:
                raise TypeError(type(x))

        # Load config Files
        try:
            config = ChainGuard.load(*existing_targets) # type: ignore
        except OSError as err:
            raise DErr.InvalidConfigError(existing_targets, *err.args) from err
        else:
            if existing_targets == [PYPROJ] and ROOT_ELEM not in config:
                raise DErr.MissingConfigError("Pyproject has no doot config")

            self.configs_loaded_from   += existing_targets
            self.config = config.remove_prefix(prefix)
            self.update_global_task_state(self.config, source=str(existing_targets))
            if bool(existing_targets):
                self.verify_config_version(self.config.on_fail(None).startup.doot_version(), source=targets)

    def _load_constants(self) -> None:
        """ Load the override constants if the loaded base config specifies one
        Modifies the global `doot.constants`
        """
        match self.config.on_fail(None).startup.constants_file(wrapper=pl.Path):
            case None:
                pass
            case pl.Path() as const_file if const_file.exists():
                self.report.trace("Loading Constants")
                base_data = ChainGuard.load(const_file)
                self.verify_config_version(base_data.on_fail(None).doot_version(), source=const_file)
                self.constants = base_data.remove_prefix(API.CONSTANT_PREFIX)

    def _load_aliases(self, *, data:Maybe[dict|ChainGuard]=None, force:bool=False) -> None:
        """ Load plugin aliases.
        if given the kwarg `data`, will *append* to the aliases
        """
        if not bool(self.aliases):
            match self.config.on_fail(API.aliases_file).startup.aliases_file(wrapper=pl.Path):
                case _ if bool(self.aliases) and not force:
                    base_data = {}
                    pass
                case pl.Path() as source if source.exists():
                    self.report.trace("Loading Aliases: %s", source)
                    base_data = ChainGuard.load(source)
                    self.verify_config_version(base_data.on_fail(None).doot_version(), source=source)
                    base_data = base_data.remove_prefix(API.ALIAS_PREFIX)
                case source:
                    self.report.trace("Alias File Not Found: %s", source)
                    base_data = {}

            # Flatten the lists
            flat = {}
            for key,val in base_data.items():
                flat[key] = {k:v for x in val for k,v in x.items()}

            # Then override with config specified plugin items:
            for key,val in self.config.on_fail({}).startup.plugins().items():
                flat[key].update(dict(val))

            self.aliases = ChainGuard(flat) # type: ignore

        match data:
            case None:
                pass
            case _ if bool(data):
                self.report.trace("Updating Aliases")
                base : dict = defaultdict(dict)
                base.update(dict(self.aliases._table()))
                for key,eps in data.items():
                    update = {x.name:x.value for x in eps}
                    base[key].update(update)

                self.aliases = ChainGuard(base)

    def _load_locations(self) -> None:
        """ Load and update the JGDVLocator db
        """
        self.report.trace("Loading Locations")
        # Load Initial locations
        for loc in self.config.on_fail([]).locations():
            try:
                for name in loc.keys():
                    self.report.trace("+ %s", name)
                    self.locs.update(loc, strict=False)
            except (JGDVError, ValueError) as err:
                self.report.error("Location Loading Failed: %s (%s)", loc, err)

    def _update_import_path(self, *paths:pl.Path) -> None:
        """ Add locations to the python path for task local code importing
        Modifies the global `sys.path`
        """
        self.report.trace("Updating Import Path")
        match paths:
            case None | []:
                task_sources = self.config.on_fail([self.locs[".tasks"]], list).startup.sources.tasks(wrapper=lambda x: [self.locs[y] for y in x])
                task_code    = self.config.on_fail([self.locs[".tasks"]], list).startup.sources.code(wrapper=lambda x: [self.locs[y] for y in x])
                paths = set(task_sources + task_code) # type: ignore
            case [*xs]:
                paths = set(paths) # type: ignore

        assert(isinstance(paths, set))
        for source in paths:
            match source:
                case pl.Path() as x if not x.exists():
                    continue
                case pl.Path() as x if not x.is_dir():
                    continue
                case pl.Path() as x:
                    # sys.path does not play nice with pl.Path
                    source_str = str(source.expanduser().resolve())
                case x:
                    raise TypeError("Bad Type for adding to sys.path", x)

            match source_str:
                case x if x in sys.path:
                    continue
                case str():
                    self.report.trace("sys.path += %s", source)
                    sys.path.append(source_str)
        else:
            self.report.trace("Import Path Updated")

class Logging_m:
    """
    Overlord management of logging and printing
    """

    def subprinter(self, name:Maybe[str]=None, *, prefix=None) -> Logger:
        """ Get a sub-printer at position `name`.
        Names are registered using JGDV.logging.LogConfig
        """
        try:
            return self.log_config.subprinter(name, prefix=prefix)
        except ValueError as err:
            raise DErr.ConfigError("Invalid Subprinter", name) from err

    def _setup_logging(self) -> None:
        self.log_config.setup(self.config)
        self.report.log = self.subprinter()
        self.report.trace("Logging Setup")

class WorkflowUtil_m:
    """ util methods on the overlord used when running a workflow """
    args : ChainGuard

    def set_parsed_cli_args(self, data:ChainGuard) -> None:
        match data:
            case _ if bool(self.args):
                raise ValueError("Setting Parsed args but its already set")
            case ChainGuard() as x if bool(x):
                self.args = data
            case x:
                raise TypeError(type(x))

    def update_global_task_state(self, data:ChainGuard, *, source:Maybe[str]=None) -> None:
        """ Try to Update the shared global state.
        Will try to get data[doot._interface.GLOBAL_STATE_KEY] data and add it to the global task state

        toml in [[state]] segments is merged here
        """
        if source is None:
            raise ValueError("Updating Global Task State must  have a source")

        self.report.trace("Updating Global State from: %s", source)
        if not isinstance(data, dict|ChainGuard):
            raise DErr.GlobalStateMismatch("Not a dict", data)

        match data.on_fail([])[API.GLOBAL_STATE_KEY]():
            case []:
                return
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
                    raise DErr.GlobalStateMismatch(x, y, source)

    def record_defaulted_config_values(self) -> None:
        if not self.config.on_fail(False).shutdown.write_defaulted_values():  # noqa: FBT003
            return

        defaulted_file : str     = self.config.on_fail("{logs}/.doot_defaults.toml", str).shutdown.defaulted_values.path()
        expanded_path  : pl.Path = self.locs[defaulted_file]
        if not expanded_path.parent.exists():
            self.report.error("Couldn't log defaulted config values to: %s", expanded_path)
            return

        defaulted_toml = ChainGuard.report_defaulted()
        with pl.Path(expanded_path).open('w') as f:
            f.write("# default values used:\n")
            f.write("\n".join(defaulted_toml) + "\n\n")

    def verify_config_version(self, ver:Maybe[str], source:str|pl.Path) -> None:
        "Ensure the config file is compatible with doot"
        doot_ver = Version(API.__version__)
        test_ver = SpecifierSet(f"~={doot_ver.major}.{doot_ver.minor}.0")
        match ver:
            case str() as x if x in test_ver:
                return
            case str() as x:
                raise DErr.VersionMismatchError("Config File is incompatible with this version of doot (%s, %s) : %s : %s", API.__version__, test_ver, x, source)
            case _:
                raise DErr.VersionMismatchError("No Doot Version Found in config file: %s", source)
##--|

@Proto(Overlord_p)
@Mixin(Startup_m, Logging_m, WorkflowUtil_m)
class DootOverlord(metaclass=MLSingleton):
    """
    The main control point of Doot
    The setup logic of doot.

    As Doot uses loaded config data throughout, using the doot.config.on_fail... pattern,
    the top-level package 'doot', uses a module getattr to offload attribute access to this class.

    """
    __version__         : str
    config              : ChainGuard
    constants           : ChainGuard
    aliases             : ChainGuard
    cmd_aliases         : ChainGuard
    args                : ChainGuard
    log_config          : JGDVLogConfig
    locs                : JGDVLocator
    configs_loaded_from : list[str|pl.Path]
    global_task_state   : dict
    path_ext            : list[str]
    is_setup            : bool
    _reporter           : Reporter_p

    def __init__(self, **kwargs:Any):
        logging.info("Creating Overlord")
        self.__version__                      = API.__version__
        self.config                           = ChainGuard()
        self.constants                        = ChainGuard.load(API.constants_file).remove_prefix(API.CONSTANT_PREFIX)
        self.aliases                          = ChainGuard()
        # TODO Remove this:
        self.cmd_aliases                      = ChainGuard()
        self.args                             = ChainGuard() # parsed arg access
        subprinters                           = self.constants.on_fail(None).printer.PRINTER_CHILDREN()
        self.log_config                       = JGDVLogConfig(subprinters=subprinters)
        self.locs                             = JGDVLocator(pl.Path.cwd()) # type: ignore
        self._reporter                        = NullReporter()
        self.configs_loaded_from              = []
        self.global_task_state                = {}
        self.path_ext                         = []
        self.is_setup                         = False

        self.null_setup()

    @property
    def report(self) -> Reporter_p:
        return self._reporter

    @report.setter
    def report(self, rep:Reporter_p) -> None:
        match rep:
            case Reporter_p():
                self._reporter = rep
            case x:
                raise TypeError(type(x))
