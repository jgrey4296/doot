#!/usr/bin/env python3
"""
Doot : An Opinionated refactor of the Doit Task Runner.

"""

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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, assert_type, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import tomlguard as TG

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot.errors
from doot.utils.check_protocol import check_protocol

# ##-- end 1st party imports

##-- data
data_path      = files("doot.__data")
constants_file = data_path.joinpath("constants.toml")
aliases_file   = data_path.joinpath("aliases.toml")
##-- end data

##-- logging
logging         = logmod.getLogger(__name__)
printer         = logmod.getLogger("doot._printer")
setup_l         = printer.getChild("setup")
fail_l          = printer.getChild("fail")
##-- end logging

__all__ = []

# Global, single points of truth:
__version__          : Final[str]         = "0.8.2"

# Can't be in doot.constants, because that isn't loaded yet
CONSTANT_PREFIX      : Final[str]         = "doot.constants"
ALIAS_PREFIX         : Final[str]         = "doot.aliases"
TOOL_PREFIX          : Final[str]         = "tool.doot"

config               : TG.TomlGuard       = TG.TomlGuard() # doot config
constants            : TG.TomlGuard       = TG.TomlGuard.load(constants_file).remove_prefix(CONSTANT_PREFIX)
aliases              : TG.TomlGuard       = TG.TomlGuard()
locs                 : DootLocData        = None # DootLocations(pl.Path()) # registered locations
args                 : TG.TomlGuard       = TG.TomlGuard() # parsed arg access
report               : Reporter_p         = None

_configs_loaded_from : list[pl.Path]      = []

def setup(targets:list[pl.Path]|False|None=None, prefix:str|None=TOOL_PREFIX) -> tuple[TG.TomlGuard, DootLocData]:
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

    logging.debug("Loading Doot Config, version: %s targets: %s", __version__, targets)
    if bool(config):
        setup_l.warning("doot.setup called even though doot is already set up")

    if bool(targets) and not any([x.exists() for x in targets]):
        raise doot.errors.DootMissingConfigError("No Doot data found")

    existing_targets       = [x for x in targets if x.exists()]

    try:
        config = TG.load(*existing_targets)
    except OSError as err:
        fail_l.error("Failed to Load Config Files: %s", existing_targets)
        raise doot.errors.DootError() from err

    config = config.remove_prefix(prefix)
    _load_constants()
    _load_aliases()
    _load_locations()
    _update_import_path()

    _configs_loaded_from   = existing_targets

    return config, locs

def _load_constants():
    """ Load the override constants if the loaded base config specifies one"""
    global constants
    setup_l.debug("Loading Constants")
    update_file = config.on_fail(None).settings.general.constants_file()
    if update_file:
        constants = TG.TomlGuard.load(pl.Path(update_file)).remove_prefix(CONSTANT_PREFIX)

def _load_aliases():
    """ Load plugin aliases """
    global aliases
    setup_l.debug("Loading Aliases")
    update_file = config.on_fail(aliases_file).settings.general.aliases_file()
    data        = TG.TomlGuard.load(pl.Path(update_file)).remove_prefix(ALIAS_PREFIX)
    # Flatten the lists
    flat = {}
    for key,val in data:
        flat[key] = {k:v for x in val for k,v in x.items()}

    # Then override with config specified:
    for key,val in config.on_fail({}).plugins().items():
        flat[key].update(dict(val))

    aliases = TG.TomlGuard(flat)

def _load_locations():
    """ Load and update the DootLocations db """
    global locs
    setup_l.debug("Loading Locations")
    # ##-- 1st party imports
    from doot.control.locations import DootLocations

    # ##-- end 1st party imports
    locs   = DootLocations(pl.Path.cwd())
    # Load Initial locations
    for loc in config.on_fail([]).locations():
        locs.update(loc)

def _update_import_path():
    """ Add locations to the python path for task local code importing  """
    setup_l.debug("Updating Import Path")
    task_sources = config.on_fail([locs[".tasks"]], list).settings.tasks.sources(wrapper=lambda x: [locs[y] for y in x])
    task_code    = config.on_fail([locs[".tasks"]], list).settings.tasks.code(wrapper=lambda x: [locs[y] for y in x])
    for source in set(task_sources + task_code):
        if source.exists() and source.is_dir():
            setup_l.debug("Adding task code directory to Import Path: %s", source)
            sys.path.append(str(source))

def _update_aliases(data:dict|TG.TomlGuard):
    global aliases
    if not bool(data):
        return

    setup_l.debug("Updating Aliases")
    base = defaultdict(dict)
    base.update(dict(aliases._table()))
    for key,eps in data.items():
        update = {x.name:x.value for x in eps}
        base[key].update(update)

    aliases = TG.TomlGuard(base)

def _test_setup():
    """
      Doesn't load anything but constants,
      Used for initialising Doot when testing.
    """
    global config, _configs_loaded_from, locs
    config               = TG.TomlGuard()
    _configs_loaded_from = []
    locs                 = None
    setup(False)
