#!/usr/bin/env python3
"""

"""
# mypy: disable-error-code="attr-defined"
# ruff: noqa: ANN001

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
from jgdv import JGDVError, Mixin, Proto
from jgdv.logging import JGDVLogConfig
from jgdv.cli._interface import ParseReport_d
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.dkey import DKey
from jgdv.structs.locator import JGDVLocator
from jgdv.structs.metalord.singleton import MLSingleton
from jgdv.util.plugins.selector import plugin_selector
from packaging.specifiers import SpecifierSet
from packaging.version import Version

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot.errors as DErr  # noqa: N812
from doot import _interface as DootAPI#  noqa: N812
from doot.reporters import BasicReporter
from doot.reporters._interface import Reporter_p

# ##-- end 1st party imports

# ##-| Local
from . import _interface as ControlAPI#  noqa: N812
from .loaders._interface import Loader_p

# # End of Imports.

# ##-- types
# isort: off
import abc
import collections.abc
from collections import defaultdict
from typing import TYPE_CHECKING, cast, assert_type, assert_never, override
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, overload

if TYPE_CHECKING:
    from importlib.metadata import EntryPoint
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from jgdv import Maybe
    from doot.errors import DootError

    type Logger = logmod.Logger
    type Loadable = DootAPI.Loadable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
##--| Controllers

class StartupController:
    type DO = DootOverlord

    def null_setup(self, obj:DO) -> None:
        """
        Doesn't load anything but constants,
        Used for initialising Doot when testing.
        Doesn't set the is_setup flag.
        """
        if obj.is_setup:
            return

        self._load_constants(obj, target=DootAPI.constants_file)
        self._load_aliases(obj, target=DootAPI.aliases_file)

    def setup(self, obj:DO, *, targets:Maybe[list[Loadable]]=None, prefix:Maybe[str]=None) -> None:
        """
        The core requirement to call before any other doot code is run.
        loads the config files, so everything else can retrieve values when imported.

        `prefix` removes a prefix from the loaded data.
        eg: 'tool.doot' for if putting doot settings in a pyproject.toml

        targets=False is for loading nothing, for testing
        """
        if obj.is_setup:
            obj.report.gen.user("doot.setup called even though doot is already set up")

        self._load_config(obj, targets=targets, prefix=prefix or DootAPI.TOOL_PREFIX)
        self._load_constants(obj,
                             target=obj.config.on_fail(None).startup.constants_file(wrapper=pl.Path))
        self._load_aliases(obj,
                           target=obj.config.on_fail(None).startup.aliases_file(wrapper=pl.Path),
                           force=True)
        self._load_locations(obj)

        # add global task state as a DKey expansion source
        DKey.add_sources(obj.global_task_state)
        obj.is_setup = True

    def _load_config(self, obj:DO, *, targets:Maybe[list[Loadable]], prefix:Maybe[str]) -> None:  # noqa: PLR0912
        """ Load a specified config, or one of the defaults if it exists """
        x                 : Any
        target_paths      : list[pl.Path]
        existing_targets  : list[pl.Path]
        ##--|
        match targets:
            case list() if bool(targets) and all([isinstance(x, pl.Path) for x in targets]):
                target_paths = [pl.Path(x) for x in targets] # type: ignore[arg-type]
            case list() if bool(targets):
                raise TypeError("Doot Config Targets should be pathlib.Path's", targets)
            case None | []:
                target_paths = [pl.Path(x) for x in obj.constants.paths.DEFAULT_LOAD_TARGETS]

        logging.log(0, "Loading Doot Config, version: %s targets: %s", DootAPI.__version__, target_paths)
        assert(isinstance(target_paths, list))
        match [x for x in target_paths if x.is_file()]:
            case [] if bool(target_paths):
                raise DErr.MissingConfigError("No Doot data found")
            case []:
                existing_targets = []
            case [*xs]:
                existing_targets = xs
            case x:
                raise TypeError(type(x))

        ##--| Load config Files
        for existing in existing_targets:
            try:
                config = ChainGuard.load(existing)
            except OSError as err:
                raise DErr.InvalidConfigError(existing_targets, *err.args) from err
            else:
                match existing:
                    case x if x.name == DootAPI.PYPROJ_TOML and DootAPI.TOOL_PREFIX not in config:
                        raise DErr.MissingConfigError("Pyproject has no doot config")
                    case x if x.name == DootAPI.DOOT_TOML:
                        chopped = config
                    case x if prefix not in config:
                        logging.warning("No Root element or prefix found in config: %s", existing)
                        chopped   = config.remove_prefix(prefix)
                        if not bool(chopped):
                            continue

                conf_ver  = chopped.on_fail(None).startup.doot_version()
                obj.verify_config_version(conf_ver, source=existing)
                obj.config = ChainGuard.merge(chopped, obj.config._table()) # type: ignore[arg-type]
                obj.configs_loaded_from.append(existing)
                obj.update_global_task_state(obj.config, source=str(existing_targets))

    def _load_constants(self, obj:DO, *, target:Maybe[Loadable]=None) -> None:
        """ Load the override constants if the loaded base config specifies one
        Modifies the global `doot.constants`
        """
        match target:
            case None:
                pass
            case pl.Path() as const_file if const_file.exists():
                obj.report.gen.trace("Loading Constants")
                base_data = ChainGuard.load(const_file)
                obj.verify_config_version(base_data.on_fail(None).doot_version(), source=const_file)
                obj.constants = base_data.remove_prefix(DootAPI.CONSTANT_PREFIX)

    def _load_aliases(self, obj:DO, *, target:Maybe[Loadable]=None, force:bool=False) -> None:
        """ Load plugin aliases from a toml file

        if forced, will append additional aliases on top of existing
        """
        final_aliases : dict            = defaultdict(dict)
        base_data     : dict|ChainGuard = {}
        target                          = target or DootAPI.aliases_file

        match bool(obj.aliases), force:
            case False, _:
                pass
            case True, True:
                final_aliases.update(dict(obj.aliases._table()))
            case True, _:
                raise RuntimeError("Tried to re-initialise aliases")

        obj.report.gen.trace("Initalising Aliases")
        match target:
            case pl.Path() as source if source.exists():
                obj.report.gen.trace("Loading Aliases: %s", source) # type: ignore[arg-type]
                base_data = ChainGuard.load(source)
                assert(isinstance(base_data, ChainGuard))
                obj.verify_config_version(base_data.on_fail(None).doot_version(), source=source)
                base_data = base_data.remove_prefix(DootAPI.ALIAS_PREFIX)
            case pl.Path() as source:
                obj.report.gen.user("Alias File Not Found: %s", source)
            case x:
                raise TypeError(type(x))

        ##--|
        # Flatten the lists
        for key,_val in base_data.items():
            _val = cast("list[dict]", _val)
            final_aliases[key] = {k:v for x in _val for k,v in x.items()}
        else:
            obj.aliases = ChainGuard(final_aliases)

    def _load_locations(self, obj:DO) -> None:
        """ Load and update the JGDVLocator db
        """
        obj.report.gen.trace("Loading Locations")
        # Load Initial locations
        for loc in obj.config.on_fail([]).locations():
            try:
                for name in loc.keys():
                    obj.report.gen.trace("+ %s", name)
                    obj.locs.update(loc, strict=False)
            except (JGDVError, ValueError) as err:
                obj.report.gen.error("Location Loading Failed: %s (%s)", loc, err)

class PluginsController:
    type DO = DootOverlord

    def load(self, obj:DO) -> None:
        self._load_plugins(obj)
        self._load_commands(obj, loader=obj.config.on_fail("default").startup.loaders.command())
        self._load_tasks(obj, loader=obj.config.on_fail("default").startup.loaders.task())

    def _load_plugins(self, obj:DootOverlord) -> None:
        """ Use the plugin loader to find all applicable `importlib.EntryPoint`s  """
        # ##-- 1st party imports
        from doot.control.loaders.plugin import PluginLoader  # noqa: PLC0415

        # ##-- end 1st party imports
        try:
            plugin_loader = PluginLoader()
            plugin_loader.setup()
            obj.loaded_plugins = plugin_loader.load()
            obj.update_aliases(data=obj.loaded_plugins) # type: ignore[attr-defined]
        except DErr.PluginError as err:
            obj.report.gen.error("Plugins Not Loaded Due to Error: %s", err) # type: ignore[attr-defined]
            raise

    def _load_commands(self, obj:DootOverlord, *, loader:str="default") -> None:
        """ Select Commands from the discovered loaded_plugins,
        using the preferred cmd loader or the default
        """
        if not bool(obj.loaded_plugins):
            raise RuntimeError("Tried to Load Commands without having loaded Plugins")

        match plugin_selector(obj.loaded_plugins.on_fail([], list).command_loader(),
                              target=loader):
            case type() as ctor:
                cmd_loader = ctor()
            case x:
                raise TypeError(type(x))

        match cmd_loader:
            case Loader_p():
                try:
                    cmd_loader.setup(obj.loaded_plugins)
                    obj.loaded_cmds = cmd_loader.load()
                except DErr.PluginError as err:
                    obj.report.gen.error("Commands Not Loaded due to Error: %s", err) # type: ignore[attr-defined]
                    obj.loaded_cmds = ChainGuard()
            case x:
                raise TypeError("Unrecognized loader type", x)

    def _load_tasks(self, obj:DootOverlord, *, loader:str="default") -> None:
        """ Load task entry points, using the preferred task loader,
        or the default
        """
        x            : Any
        task_loader  : Loader_p
        ##--|
        match plugin_selector(obj.loaded_plugins.on_fail([], list).task_loader(),
                              target=loader):
            case type() as ctor:
                task_loader = ctor()
            case x:
                raise TypeError(type(x))

        match task_loader:
            case Loader_p():
                task_loader.setup(obj.loaded_plugins)
                obj.loaded_tasks = task_loader.load()
            case x:
                raise TypeError("Unrecognised loader type", x)

##--| Overlord

@Proto(ControlAPI.Overlord_i)
class DootOverlord:
    """
    The main control point of Doot
    The setup logic of doot.

    As Doot uses loaded config data throughout, using the doot.config.on_fail... pattern,
    the top-level package 'doot', uses a module getattr to offload attribute access to this class.

    Adapted from https://stackoverflow.com/questions/880530
    """

    _startup             : ClassVar[StartupController]   = StartupController()
    _plugin              : ClassVar[PluginsController]   = PluginsController()

    __version__          : str
    global_task_state    : dict[str, Any]
    path_ext             : list[str]
    configs_loaded_from  : list[str|pl.Path]
    is_setup             : bool

    def __init__(self, *args:Any, **kwargs:Any):
        super().__init__(*args, **kwargs)
        logging.info("Creating Overlord")
        empty_chain               = ChainGuard()
        self.__version__          = DootAPI.__version__
        self.global_task_state    = {}
        self.path_ext             = []
        self.configs_loaded_from  = []
        self.is_setup             = False
        self.config               = empty_chain
        self.constants            = empty_chain
        self.aliases              = empty_chain
        self.loaded_plugins       = empty_chain
        self.loaded_cmds          = empty_chain
        self.loaded_tasks         = empty_chain
        # TODO Remove this:
        self.cmd_aliases  = ChainGuard()
        self.args         = ChainGuard()  # parsed arg access
        self.locs         = JGDVLocator(pl.Path.cwd())
        self.report       = BasicReporter()

        DootOverlord._startup.null_setup(self)

    @property
    def report(self) -> Reporter_p:
        return self._reporter

    @report.setter
    def report(self, rep:Any) -> None:
        self._set_reporter(rep)

    ##--| internal methods

    def _set_reporter(self, rep:Any) -> None:
        match rep:
            case Reporter_p():
                self._reporter = rep
            case x:
                raise TypeError(type(x))

    ##--| public methods

    def setup(self, *, targets:Maybe[list[Loadable]]=None, prefix:Maybe[str]=None) -> None:
        self._startup.setup(self, targets=targets, prefix=prefix)
        self.update_import_path()

    def load(self) -> None:
        self._plugin.load(self)

    def load_reporter(self, target:str="default") -> None:
        if not bool(self.loaded_plugins):
            raise RuntimeError("Tried to Load Reporter without loading loaded_plugins")

        match plugin_selector(self.loaded_plugins.on_fail([], list).reporter(),
                              target=target):
            case type() as ctor:
                self.report = ctor() # type: ignore[attr-defined]
            case x:
                raise TypeError(type(x))

    def verify_config_version(self, ver:Maybe[str], source:Maybe[str|pl.Path], *, override:Maybe[str]=None) -> None:
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

    def update_aliases(self, *, data:dict|ChainGuard) -> None:
        """
        Update aliases with a dict-like of loaded mappings
        """
        final_aliases : dict
        if not bool(data):
            return

        final_aliases = defaultdict(dict)
        final_aliases.update(dict(self.aliases._table()))

        for key,eps in data.items():
            eps     = cast("list[EntryPoint]", eps)
            update  = {x.name:x.value for x in eps} # type: ignore[union-attr]
            final_aliases[key].update(update)
        else:
            self.aliases = ChainGuard(final_aliases)

    def update_global_task_state(self, data:ChainGuard, *, source:Maybe[str]=None) -> None:
        """ Try to Update the shared global state.
        Will try to get data[doot._interface.GLOBAL_STATE_KEY] data and add it to the global task state

        toml in [[state]] segments is merged here
        """
        if source is None:
            raise ValueError("Updating Global Task State must  have a source")

        self.report.gen.detail("Updating Global State from: %s", source)
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

    def update_import_path(self, *paths:pl.Path) -> None:
        """ Add locations to the python path for task local code importing
        Modifies the global `sys.path`
        """
        x         : Any
        combined  : set[pl.Path]
        ##--| Wrappers
        def loc_wrapper(x) -> list[pl.Path]:
            return [self.locs[y] for y in x]

        ##--|
        self.report.gen.trace("Updating Import Path")
        match paths:
            case None | []:
                task_sources  = self.config.on_fail([self.locs[".tasks"]], list).startup.sources.tasks(wrapper=loc_wrapper)
                task_code     = self.config.on_fail([self.locs[".tasks"]], list).startup.sources.code(wrapper=loc_wrapper)
                combined = set(task_sources + task_code)
            case [*xs]:
                combined = set(paths)

        assert(isinstance(combined, set))
        for source in combined:
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
                    self.report.gen.trace("sys.path += %s", str(source))
                    sys.path.append(source_str)
        else:
            self.report.gen.trace("Import Path Updated")

    def update_cmd_args(self, data:ParseReport_d|dict, *,  override:bool=False) -> None:
        """ update global args that cmd's use for control flow """
        prepared : dict
        ##--|
        match data:
            case _ if bool(self.args) and not override:
                raise ValueError("Setting Parsed args but its already set")
            case {"prog": dict() as prog, "cmds": dict() as cmds, "subs": list() as subs, "help": bool() as _help}:
                prepared = {
                    "prog" : prog,
                    "cmds" : cmds,
                    "subs" : subs,
                    "help" : _help,
                }
            case ParseReport_d():
                prepared = data.to_dict()
            case x:
                raise TypeError(type(x))

        ##--|
        assert(bool(prepared))
        assert(all(x in prepared for x in ["prog", "cmds", "subs", "help"]))
        assert(isinstance(prepared['cmds'], dict))
        assert(isinstance(prepared['subs'], dict))
        # Handle 'help'
        match prepared:
            case _ if not prepared['help']:
                pass
            case {"subs": _subs} if bool(_subs):
                prepared['cmds'].clear()
                prepared['cmds']['help'] = []
                prepared['cmds']['help'] += [{"name":"help", "args":{"target": x}} for x in _subs.keys()]
            case {"cmds": _cmds} if bool(_cmds):
                keys = list(_cmds.keys())
                prepared['cmds'].clear()
                prepared['cmds']['help'] = []
                prepared['cmds']['help'] += [{"name":"help", "args":{"target": x}} for x in keys]


        self.args = ChainGuard(prepared)

##--| Facade

class OverlordFacade(types.ModuleType):
    """
    A Facade for the overlord, to be used as the module class
    of the root package 'doot'.

    """
    _overlord : ControlAPI.Overlord_i

    def __init__(self, *args, **kwargs) -> None: # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)
        self._overlord = cast("ControlAPI.Overlord_i", DootOverlord())

    @override
    def __getattr__(self, key):
        return getattr(self._overlord, key)
