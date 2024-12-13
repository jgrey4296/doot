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
from jgdv import check_protocol, Maybe, VerStr
from jgdv.structs.chainguard import ChainGuard
from jgdv.logging import JGDVLogConfig
from jgdv.structs.strang.locations import JGDVLocations as DootLocations
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot.errors

# ##-- end 1st party imports

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
CONSTANT_PREFIX      : Final[str]         = "doot.constants"
ALIAS_PREFIX         : Final[str]         = "doot.aliases"
TOOL_PREFIX          : Final[str]         = "tool.doot"

config               : ChainGuard         = ChainGuard() # doot config
constants            : ChainGuard         = ChainGuard.load(constants_file).remove_prefix(CONSTANT_PREFIX)
aliases              : ChainGuard         = ChainGuard()
locs                 : DootLocations      = None # DootLocations(pl.Path()) # registered locations
args                 : ChainGuard         = ChainGuard() # parsed arg access
log_config           : JGDVLogConfig      = JGDVLogConfig(constants.on_fail(None).printer.PRINTER_CHILDREN())

_configs_loaded_from : list[pl.Path]      = []

def subprinter(name=None) -> logmod.Logger:
    """ Get a sub-printer at position `name`.
    Names are registered using JGDV.logging.LogConfig
    """
    return log_config.subprinter(name)

def setup(targets:Maybe[list[pl.Path]|False]=None, prefix:Maybe[str]=TOOL_PREFIX) -> tuple[ChainGuard, DootLocations]:
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
        logging.warning("doot.setup called even though doot is already set up")

    existing_targets       = [x for x in targets if x.exists()]

    if bool(targets) and not bool(existing_targets):
        raise doot.errors.DootMissingConfigError("No Doot data found")

    try:
        config = ChainGuard.load(*existing_targets)
    except OSError as err:
        logging.error("Failed to Load Config Files: %s", existing_targets)
        raise doot.errors.DootError() from err

    if existing_targets == [pl.Path("pyproject.toml")] and "doot" not in config:
        raise doot.errors.DootMissingConfigError("Pyproject has no doot config")

    config = config.remove_prefix(prefix)
    log_config.setup(config)
    _load_constants()
    _load_aliases()
    _load_locations()
    _update_import_path()
    _configs_loaded_from   = existing_targets

    return config, locs

def _load_constants():
    """ Load the override constants if the loaded base config specifies one"""
    global constants
    match config.on_fail(None).settings.general.constants_file(wrapper=pl.Path):
        case None:
            pass
        case pl.Path() as const_file if const_file.exists():
            logging.info("---- Loading Constants")
            constants = ChainGuard.load(const_file).remove_prefix(CONSTANT_PREFIX)

def _load_aliases():
    """ Load plugin aliases """
    global aliases
    logging.info("---- Loading Aliases")
    match config.on_fail(aliases_file).settings.general.aliases_file(wrapper=pl.Path):
        case pl.Path() as update_file if update_file.exists():
            data = ChainGuard.load(update_file).remove_prefix(ALIAS_PREFIX)

    # Flatten the lists
    flat = {}
    for key,val in data:
        flat[key] = {k:v for x in val for k,v in x.items()}

    # Then override with config specified:
    for key,val in config.on_fail({}).plugins().items():
        flat[key].update(dict(val))

    aliases = ChainGuard(flat)

def _load_locations():
    """ Load and update the DootLocations db """
    global locs
    logging.info("---- Loading Locations")
    locs   = DootLocations(pl.Path.cwd())
    # Load Initial locations
    for loc in config.on_fail([]).locations():
        locs.update(loc, strict=False)

def _update_import_path():
    """ Add locations to the python path for task local code importing  """
    logging.info("---- Updating Import Path")
    task_sources = config.on_fail([locs[".tasks"]], list).settings.tasks.sources(wrapper=lambda x: [locs[y] for y in x])
    task_code    = config.on_fail([locs[".tasks"]], list).settings.tasks.code(wrapper=lambda x: [locs[y] for y in x])
    for source in set(task_sources + task_code):
        if source.exists() and source.is_dir():
            logging.debug("Adding task code directory to Import Path: %s", source)
            sys.path.append(str(source))

def _update_aliases(data:dict|ChainGuard):
    global aliases
    if not bool(data):
        return

    logging.info("---- Updating Aliases")
    base = defaultdict(dict)
    base.update(dict(aliases._table()))
    for key,eps in data.items():
        update = {x.name:x.value for x in eps}
        base[key].update(update)

    aliases = ChainGuard(base)

def _test_setup():
    """
      Doesn't load anything but constants,
      Used for initialising Doot when testing.
    """
    global config, _configs_loaded_from, locs
    config               = ChainGuard()
    _configs_loaded_from = []
    locs                 = None
    setup(False)
