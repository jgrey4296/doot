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
from jgdv.util.plugins.selector import plugin_selector

# ##-- end 3rd party imports

# ##-- 1st party imports
from doot import _interface as DootAPI#  noqa: N812
from . import _interface as ControlAPI  # noqa: N812
import doot.errors as DErr  # noqa: N812
from doot.reporters import BasicReporter
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
from typing import no_type_check, final, overload
from doot.reporters._interface import Reporter_p

if TYPE_CHECKING:
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from logmod import Logger

    from jgdv import Maybe
    from doot.errors import DootError
    from doot.reporters._interface import Reporter_i

    type Loadable = DootAPI.Loadable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:

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

        self.load_constants(target=DootAPI.constants_file)
        self.load_aliases(target=DootAPI.aliases_file)

    def setup(self, *, targets:Maybe[list[Loadable]]=None, prefix:str=DootAPI.TOOL_PREFIX) -> None:
        """
        The core requirement to call before any other doot code is run.
        loads the config files, so everything else can retrieve values when imported.

        `prefix` removes a prefix from the loaded data.
        eg: 'tool.doot' for if putting doot settings in a pyproject.toml

        targets=False is for loading nothing, for testing
        """
        if self.is_setup:
            self.report.user("doot.setup called even though doot is already set up") # type: ignore

        self.load_config(targets=targets, prefix=prefix)
        self.setup_logging() # type: ignore
        self.load_constants(target=self.config.on_fail(None).startup.constants_file(wrapper=pl.Path)) # type: ignore
        self.load_aliases(target=self.config.on_fail(None).startup.aliases_file(wrapper=pl.Path), force=True) # type: ignore
        self.load_locations()
        self.update_import_path()

        # add global task state as a DKey expansion source
        DKey.add_sources(self.global_task_state)
        self.is_setup = True

    def load_config(self, *, targets:Maybe[list[Loadable]], prefix:Maybe[str]) -> None:
        """ Load a specified config, or one of the defaults if it exists """
        match targets:
            case list() if bool(targets) and all([isinstance(x, pl.Path) for x in targets]):
                targets : list[pl.Path] = [pl.Path(x) for x in targets] # type: ignore
            case list() if bool(targets):
                raise TypeError("Doot Config Targets should be pathlib.Path's", targets)
            case None | []:
                targets : list[pl.Path] = [pl.Path(x) for x in self.constants.paths.DEFAULT_LOAD_TARGETS] # type: ignore

        logging.log(0, "Loading Doot Config, version: %s targets: %s", DootAPI.__version__, targets)

        assert(isinstance(targets, list))
        match [x for x in targets if x.is_file()]:
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
            if existing_targets == [ControlAPI.PYPROJ] and ControlAPI.ROOT_ELEM not in config:
                raise DErr.MissingConfigError("Pyproject has no doot config")

            self.configs_loaded_from   += existing_targets
            self.config = config.remove_prefix(prefix)
            self.update_global_task_state(self.config, source=str(existing_targets))
            if bool(existing_targets):
                self.verify_config_version(self.config.on_fail(None).startup.doot_version(), source=targets)

    def load_constants(self, *, target:Maybe[Loadable]=None) -> None:
        """ Load the override constants if the loaded base config specifies one
        Modifies the global `doot.constants`
        """
        match target:
            case None:
                pass
            case pl.Path() as const_file if const_file.exists():
                self.report.trace("Loading Constants")
                base_data = ChainGuard.load(const_file)
                self.verify_config_version(base_data.on_fail(None).doot_version(), source=const_file)
                self.constants = base_data.remove_prefix(DootAPI.CONSTANT_PREFIX)

    def load_aliases(self, *, target:Maybe[Loadable]=None, force:bool=False) -> None:
        """ Load plugin aliases from a toml file

        if forced, will append additional aliases on top of existing
        """
        final_aliases : dict            = defaultdict(dict)
        base_data     : dict|ChainGuard = {}
        target                          = target or DootAPI.aliases_file

        match bool(self.aliases), force:
            case False, _:
                pass
            case True, True:
                final_aliases.update(dict(self.aliases._table()))
            case True, _:
                raise RuntimeError("Tried to re-initialise aliases")

        self.report.trace("Initalising Aliases")
        match target:
            case pl.Path() as source if source.exists():
                self.report.trace("Loading Aliases: %s", source)
                base_data = ChainGuard.load(source)
                assert(isinstance(base_data, ChainGuard))
                self.verify_config_version(base_data.on_fail(None).doot_version(), source=source)
                base_data = base_data.remove_prefix(DootAPI.ALIAS_PREFIX)
            case pl.Path() as source:
                self.report.user("Alias File Not Found: %s", source)
            case x:
                raise TypeError(type(x))

        ##--|
        # Flatten the lists
        for key,val in base_data.items():
            final_aliases[key] = {k:v for x in val for k,v in x.items()} # type: ignore
        else:
            self.aliases = ChainGuard(final_aliases)

    def update_aliases(self, *, data:dict|ChainGuard) -> None:
        """
        Update aliases with a dict-like of loaded mappings
        """
        if not bool(data):
            return

        final_aliases : dict = defaultdict(dict)
        final_aliases.update(dict(self.aliases._table()))

        for key,eps in data.items():
            update = {x.name:x.value for x in eps} # type: ignore
            final_aliases[key].update(update)
        else:
            self.aliases = ChainGuard(final_aliases)

    def load_locations(self) -> None:
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

    def setup_logging(self) -> None:
        self.log_config.setup(self.config)

class Plugins_m:

    def load_plugins(self) -> None:
        """ Use the plugin loader to find all applicable `importlib.EntryPoint`s  """
        from doot.control.loaders.plugin import PluginLoader
        try:
            self.plugin_loader = PluginLoader()
            self.plugin_loader.setup()
            self.loaded_plugins : ChainGuard = self.plugin_loader.load()
            self.update_aliases(data=self.loaded_plugins) # type: ignore[attr-defined]
        except DErr.PluginError as err:
            self.report.error("Plugins Not Loaded Due to Error: %s", err) # type: ignore[attr-defined]
            raise

    def load_reporter(self, target:str="default") -> None:
        if not bool(self.loaded_plugins):
            raise RuntimeError("Tried to Load Reporter without loading loaded_plugins")

        match plugin_selector(self.loaded_plugins.on_fail([], list).reporter(),
                              target=target): # type: ignore
            case type() as ctor:
                self.report = ctor(logger=self.log_config.subprinter()) # type: ignore[attr-defined]
            case x:
                raise TypeError(type(x))


    def load_commands(self, *, loader:str="default") -> None:
        """ Select Commands from the discovered loaded_plugins,
        using the preferred cmd loader or the default
        """
        if not bool(self.loaded_plugins):
            raise RuntimeError("Tried to Load Commands without having loaded Plugins")

        match plugin_selector(self.loaded_plugins.on_fail([], list).command_loader(), # type: ignore
                              target=loader):
            case type() as ctor:
                self.cmd_loader = ctor()
            case x:
                raise TypeError(type(x))

        from .loaders._interface import Loader_p
        match self.cmd_loader:
            case Loader_p():
                try:
                    self.cmd_loader.setup(self.loaded_plugins)
                    self.loaded_cmds = self.cmd_loader.load()
                except DErr.PluginError as err:
                    self.report.error("Commands Not Loaded due to Error: %s", err) # type: ignore[attr-defined]
                    self.loaded_cmds = ChainGuard()
            case x:
                raise TypeError("Unrecognized loader type", x)

    def load_tasks(self, *, loader:str="default") -> None:
        """ Load task entry points, using the preferred task loader,
        or the default
        """
        match plugin_selector(self.loaded_plugins.on_fail([], list).task_loader(), # type: ignore
                              target=loader):
            case type() as ctor:
                self.task_loader = ctor()
            case x:
                raise TypeError(type(x))

        from .loaders._interface import Loader_p
        match self.task_loader:
            case Loader_p():
                self.task_loader.setup(self.loaded_plugins)
                self.loaded_tasks = self.task_loader.load()
            case x:
                raise TypeError("Unrecognised loader type", x)

class WorkflowUtil_m:
    """ util methods on the overlord used when running a workflow """
    args : ChainGuard

    def set_parsed_cli_args(self, data:ChainGuard, *, override:bool=False) -> None:
        match data:
            case _ if bool(self.args) and not override:
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

        self.report.detail("Updating Global State from: %s", source)
        if not isinstance(data, dict|ChainGuard):
            raise DErr.GlobalStateMismatch("Not a dict", data)

        match data.on_fail([])[DootAPI.GLOBAL_STATE_KEY]():
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

    def verify_config_version(self, ver:Maybe[str], source:str|pl.Path, *, override:Maybe[str]=None) -> None:
        """Ensure the config file is compatible with doot

        Compatibility is based on MAJOR.MINOR and discards PATCH

        Raises a VersionMismatchError otherwise if they aren't compatible
        """
        doot_ver = Version(override or DootAPI.__version__)
        test_ver = SpecifierSet(f"~={doot_ver.major}.{doot_ver.minor}.0")
        match ver:
            case str() as x if x in test_ver:
                return
            case str() as x:
                raise DErr.VersionMismatchError("Config File is incompatible with this version of doot (%s, %s) : %s : %s", DootAPI.__version__, test_ver, x, source)
            case _:
                raise DErr.VersionMismatchError("No Doot Version Found in config file: %s", source)

    def update_import_path(self, *paths:pl.Path) -> None:
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

##--|

@Proto(ControlAPI.Overlord_i)
@Mixin(Startup_m, Plugins_m, WorkflowUtil_m)
class DootOverlord:
    """
    The main control point of Doot
    The setup logic of doot.

    As Doot uses loaded config data throughout, using the doot.config.on_fail... pattern,
    the top-level package 'doot', uses a module getattr to offload attribute access to this class.

    Adapted from https://stackoverflow.com/questions/880530
    """

    def __init__(self, *args:Any, **kwargs:Any):
        super().__init__(*args, **kwargs)
        logging.info("Creating Overlord")
        self.__version__                             = DootAPI.__version__
        self.global_task_state   : dict[str, Any]    = {}
        self.path_ext            : list[str]         = []
        self.configs_loaded_from : list[str|pl.Path] = []
        self.is_setup                                = False
        self.config                                  = ChainGuard()
        self.constants                               = ChainGuard()
        self.aliases                                 = ChainGuard()
        self.loaded_plugins                          = ChainGuard()
        self.loaded_cmds                             = ChainGuard()
        self.loaded_tasks                            = ChainGuard()
        # TODO Remove this:
        self.cmd_aliases                      = ChainGuard()
        self.args                             = ChainGuard() # parsed arg access
        self.locs                             = JGDVLocator(pl.Path.cwd()) # type: ignore
        # TODO move to main
        self.log_config                       = JGDVLogConfig()
        # TODO fix this:
        self.report                           = BasicReporter() # type: ignore

        self.null_setup()

    @property
    def report(self) -> Reporter_i:
        return self._reporter

    @report.setter
    def report(self, rep:Reporter_i) -> None:
        self.set_reporter(rep)

    def set_reporter(self, rep:Reporter_i) -> None:
        match rep:
            case Reporter_p():
                self._reporter = rep
            case x:
                raise TypeError(type(x))

class OverlordFacade(types.ModuleType):
    """
    A Facade for the overlord, to be used as the module class
    of the root package 'doot'.

    """
    _overlord : ControlAPI.Overlord_i

    def __init__(self, *args, **kwargs) -> None: # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)
        self._overlord = cast("ControlAPI.Overlord_i", DootOverlord())

    def __getattr__(self, key):
        return getattr(self._overlord, key)
