#!/usr/bin/env python3
"""
Doot : An Opinionated refactor of the Doit Task Runner.



"""
##-- std imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import Final, Any, assert_type
##-- end std imports

import sys
import tomlguard as TG
import doot.errors
from doot import constants
from doot.control.locations import DootLocations
from doot._abstract.reporter import Reporter_i
from doot.utils.check_protocol import check_protocol

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging
printer         = logmod.getLogger("doot._printer")

# Global, single points of truth:
__version__          : Final[str]         = "0.5.0"

config               : TG.TomlGuard       = TG.TomlGuard() # doot config
locs                 : DootLocData        = DootLocations(pl.Path()) # registered locations
args                 : TG.TomlGuard       = TG.TomlGuard() # parsed arg access
report               : Reporter_i         = None

_configs_loaded_from : list[pl.Path]      = []

def setup(targets:list[pl.Path]|None=None, prefix:str|None=None) -> tuple[TG.TomlGuard, DootLocData]:
    """
      The core requirement to call before any other doot code is run.
      loads the config files, so everything else can retrieve values when imported.
    """
    global config, locs, _configs_loaded_from
    targets : list[pl.Path] = targets or constants.DEFAULT_LOAD_TARGETS
    logging.debug("Loading Doot Config, version: %s targets: %s", __version__, targets)
    if bool(config):
        raise Exception("Setup called even though doot is already set up")

    if not all([isinstance(x, pl.Path) for x in targets]):
        raise TypeError("Doot Config Targets should be pathlib.Path's")

    if not any([x.exists() for x in targets]):
        raise doot.errors.DootMissingConfigError("No Doot data found")

    existing_targets       = [x for x in targets if x.exists()]

    try:
        config = TG.load(*existing_targets)
    except OSError:
        logging.error("Failed to Load Config Files: %s", existing_targets)
        raise doot.errors.DootError()

    locs   = DootLocations(pl.Path.cwd())

    # Load Initial locations
    for loc in config.locations:
        locs.update(loc)

    _configs_loaded_from   = existing_targets

    match prefix:
        case None:
            pass
        case str():
            logging.debug("Removing prefix from config data: %s", prefix)
            for x in prefix.split("."):
                config = config[x]

    task_sources       = config.on_fail([".tasks"], list).settings.tasks.sources(wrapper=lambda x: [locs[y] for y in x])
    task_code          = config.on_fail([".tasks"], list).settings.tasks.code(wrapper=lambda x: [locs[y] for y in x])
    for source in set(task_sources + task_code):
        if source.exists() and source.is_dir():
            logging.debug("Adding task code directory to Import Path: %s", source)
            sys.path.append(str(source))

    return config, locs
