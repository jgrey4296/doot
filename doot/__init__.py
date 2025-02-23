#!/usr/bin/env python3
"""
Doot : An Opinionated refactor of the Doit Task Runner.

"""
# ruff: noqa: ANN001, PLW0603, FBT003
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import sys
from collections import defaultdict
from importlib.resources import files
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Maybe, VerStr
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.dkey import DKey
from jgdv.logging import JGDVLogConfig
from jgdv.structs.locator import JGDVLocator as DootLocator
from jgdv import JGDVError
from packaging.specifiers import SpecifierSet
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot.errors

# ##-- end 1st party imports

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

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

# isort: on
# ##-- end types

##-- data
data_path      = files("doot.__data")
constants_file = data_path.joinpath("constants.toml")
aliases_file   = data_path.joinpath("aliases.toml")
##-- end data

##-- logging
logging         = logmod.getLogger(__name__)
##-- end logging

# Global, single points of truth:
__version__          : Final[VerStr]         = "0.13.0"

# Can't be in doot.constants, because that isn't loaded yet
CONSTANT_PREFIX       : Final[str]         = "doot.constants"
ALIAS_PREFIX          : Final[str]         = "doot.aliases"
TOOL_PREFIX           : Final[str]         = "tool.doot"

config                : ChainGuard         = ChainGuard()
constants             : ChainGuard         = ChainGuard.load(constants_file).remove_prefix(CONSTANT_PREFIX)
aliases               : ChainGuard         = ChainGuard()
cmd_aliases           : ChainGuard         = ChainGuard()
locs                  : DootLocator        = None # DootLocator(pl.Path()) # registered locations
args                  : ChainGuard         = ChainGuard() # parsed arg access
log_config            : JGDVLogConfig      = JGDVLogConfig(constants.on_fail(None).printer.PRINTER_CHILDREN())

_global_task_state    : ChainGuard         = dict()
_configs_loaded_from  : list[pl.Path]      = []

def subprinter(name=None) -> logmod.Logger:
    """ Get a sub-printer at position `name`.
    Names are registered using JGDV.logging.LogConfig
    """
    try:
        return log_config.subprinter(name)
    except ValueError as err:
        raise doot.errors.ConfigError("Invalid Subprinter", name) from err

def setup(targets:Maybe[list[pl.Path]|False]=None, prefix:Maybe[str]=TOOL_PREFIX) -> tuple[ChainGuard, DootLocator]:
    """
      The core requirement to call before any other doot code is run.
      loads the config files, so everything else can retrieve values when imported.

      `prefix` removes a prefix from the loaded data.
      eg: 'tool.doot' for if putting doot settings in a pyproject.toml

      targets=False is for loading nothing, for testing
    """
    global config, _configs_loaded_from
    match targets:
        case False:
            targets :list[pl.Path] = []
        case list() if bool(targets) and all([isinstance(x, pl.Path) for x in targets]):
            targets : list[pl.Path] = [pl.Path(x) for x in targets]
        case list() if bool(targets):
            raise TypeError("Doot Config Targets should be pathlib.Path's", targets)
        case _:
            targets : list[pl.Path] = [pl.Path(x) for x in constants.paths.DEFAULT_LOAD_TARGETS]

    logging.log(0, "Loading Doot Config, version: %s targets: %s", __version__, targets)
    if bool(config):
        logging.warning("doot.setup called even though doot is already set up")

    existing_targets       = [x for x in targets if x.exists()]

    if bool(targets) and not bool(existing_targets):
        raise doot.errors.MissingConfigError("No Doot data found")

    try:
        config = ChainGuard.load(*existing_targets)
    except OSError as err:
        raise doot.errors.InvalidConfigError(existing_targets, *err.args) from err

    if existing_targets == [pl.Path("pyproject.toml")] and "doot" not in config:
        raise doot.errors.MissingConfigError("Pyproject has no doot config")

    config = config.remove_prefix(prefix)

    if bool(targets):
        verify_config_version(config.on_fail(None).startup.doot_version(), source=targets)

    log_config.setup(config)
    _load_constants()
    _load_aliases()
    _load_locations()
    _update_import_path()
    _set_command_aliases()
    for x in config.on_fail([])['global'].state():
        update_global_task_state(x, source="doot.toml")
    else:
        DKey.add_sources(_global_task_state)

    _configs_loaded_from   = existing_targets
    return config, locs

def verify_config_version(ver:Maybe[str], source:str|pl.Path) -> None:
    "Ensure the config file is compatible with doot"
    doot_ver = SpecifierSet(f"~={__version__}")
    match ver:
        case str() as x if x in doot_ver:
            return
        case str() as x:
            raise doot.errors.VersionMismatchError("Config File is incompatible with this version of doot (%s) : %s : %s", __version__, x, source)
        case _:
            raise doot.errors.VersionMismatchError("No Doot Version Found in config file: %s", source)

def update_global_task_state(data:dict|ChainGuard, *, source=None) -> None:
    """ Update the shared global state.
    expects a dict of the immediate date.

    toml in [[state]] segments is merged here
    """
    assert(source is not None)
    setup_l = subprinter("setup")
    setup_l.trace("Updating Global State from: %s", source)
    if not isinstance(data, dict|ChainGuard):
        raise doot.errors.GlobalStateMismatch("Not a dict", data)

    for x,y in data.items():
        if x not in _global_task_state:
            _global_task_state[x] = y
        elif _global_task_state[x] != y:
            raise doot.errors.GlobalStateMismatch(x, y, source)

def _load_constants() -> None:
    """ Load the override constants if the loaded base config specifies one
    Modifies the global `doot.constants`
    """
    global constants
    setup_l = subprinter("setup")
    match config.on_fail(None).startup.constants_file(wrapper=pl.Path):
        case None:
            pass
        case pl.Path() as const_file if const_file.exists():
            setup_l.trace("Loading Constants")
            base_data = ChainGuard.load(const_file)
            verify_config_version(base_data.on_fail(None).doot_version(), source=const_file)
            constants = base_data.remove_prefix(CONSTANT_PREFIX)

def _load_aliases(*, data:Maybe[dict|ChainGuard]=None, force:bool=False) -> None:
    """ Load plugin aliases.
    if given the kwarg `data`, will *append* to the aliases
    Modifies the global `doot.aliases`
    """
    global aliases
    setup_l = subprinter("setup")
    if not bool(aliases):
        match config.on_fail(aliases_file).startup.aliases_file(wrapper=pl.Path):
            case _ if bool(aliases) and not force:
                base_data = {}
                pass
            case pl.Path() as source if source.exists():
                setup_l.trace("Loading Aliases: %s", source)
                base_data = ChainGuard.load(source)
                verify_config_version(base_data.on_fail(None).doot_version(), source=source)
                base_data = base_data.remove_prefix(ALIAS_PREFIX)
            case   source:
                setup_l.trace("Alias File Not Found: %s", source)
                base_data = {}

        # Flatten the lists
        flat = {}
        for key,val in base_data.items():
            flat[key] = {k:v for x in val for k,v in x.items()}

        # Then override with config specified plugin items:
        for key,val in config.on_fail({}).startup.plugins().items():
            flat[key].update(dict(val))

        aliases = ChainGuard(flat)

    match data:
        case None:
            pass
        case _ if bool(data):
            setup_l.trace("Updating Aliases")
            base = defaultdict(dict)
            base.update(dict(aliases._table()))
            for key,eps in data.items():
                update = {x.name:x.value for x in eps}
                base[key].update(update)

            aliases = ChainGuard(base)

def _load_locations() -> None:
    """ Load and update the DootLocator db
    Modifies the global `doot.locs`
    """
    global locs
    setup_l = subprinter("setup")
    setup_l.trace("Loading Locations")
    locs   = DootLocator(pl.Path.cwd())
    # Load Initial locations
    for loc in config.on_fail([]).locations():
        try:
            for name in loc.keys():
                setup_l.trace("+ %s", name)
                locs.update(loc, strict=False)
        except (JGDVError, ValueError) as err:
            setup_l.error("Location Loading Failed: %s (%s)", loc, err)

def _update_import_path() -> None:
    """ Add locations to the python path for task local code importing
    Modifies the global `sys.path`
    """
    setup_l = subprinter("setup")
    setup_l.trace("Updating Import Path")
    task_sources = config.on_fail([locs[".tasks"]], list).startup.sources.tasks(wrapper=lambda x: [locs[y] for y in x])
    task_code    = config.on_fail([locs[".tasks"]], list).startup.sources.code(wrapper=lambda x: [locs[y] for y in x])
    for source in set(task_sources + task_code):
        match source:
            case None:
                pass
            case x if x.exists() and x.is_dir():
                setup_l.trace("+ %s", source)
                sys.path.append(str(source))

def _set_command_aliases() -> None:
    """ Read settings.commands.* and register aliases """
    global cmd_aliases
    setup_l = subprinter("setup")
    setup_l.trace("Setting Command Aliases")
    registered = {}
    for name,details in config.on_fail({}).settings.commands().items():
        for alias, args in details.on_fail({}, non_root=True).aliases().items():
            setup_l.trace("- %s -> %s", name, alias)
            registered[alias] = [name, *args]
    else:
        cmd_aliases = ChainGuard(registered)
        setup_l.trace("Finished Command Aliases")

def _null_setup() -> None:
    """
      Doesn't load anything but constants,
      Used for initialising Doot when testing.
    """
    global config, _configs_loaded_from, locs
    config               = ChainGuard()
    _configs_loaded_from = []
    locs                 = None
    setup(False)

def _test_setup() -> None:
    """ Deprecated, use _null_setup """
    _null_setup()
