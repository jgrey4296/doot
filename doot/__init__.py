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

import tomler
import doot.errors
from doot import constants
from doot.control.locations import DootLocations
from doot._abstract.reporter import Reporter_i
from doot.utils.check_protocol import check_protocol

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Global, single points of truth:
__version__          : Final[str]      = "0.2.0"

config               : tomler.Tomler   = tomler.Tomler() # doot config
locs                 : DootLocData     = DootLocations(pl.Path()) # registered locations
args                 : tomler.Tomler   = tomler.Tomler() # parsed arg access
report               : Reporter_i      = None

_configs_loaded_from : list[pl.Path] = []

def setup(targets:list[pl.Path]|None=None, prefix:str|None=None) -> tuple[tomler.Tomler, DootLocData]:
    """
      The core requirement to call before any other doot code is run.
      loads the config files, so everything else can retrieve values when imported.
    """
    global config, locs, _configs_loaded_from
    targets : list[pl.Path] = targets or constants.DEFAULT_LOAD_TARGETS
    logging.debug("Loading Doot Config, version: %s targets: %s", __version__, targets)
    if config is not None:
        raise Exception("Setup called even though doot is already set up")

    if not all([isinstance(x, pl.Path) for x in targets]):
        raise TypeError("Doot Config Targets should be pathlib.Path's")

    if not any([x.exists() for x in targets]):
        raise doot.errors.DootConfigError("No Doot data found")

    existing_targets       = [x for x in targets if x.exists()]

    config = tomler.load(*existing_targets)
    locs   = DootLocations(pl.Path.cwd())

    for loc in config.locations:
        locs.update(loc)

    _configs_loaded_from   = existing_targets

    match prefix:
        case None:
            return config, locs
        case str():
            for x in prefix.split("."):
                config = config[x]

    return config, locs
