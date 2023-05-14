#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
from importlib import resources

from doot import constants
from doot.control.locations import DootLocData
from doot.task.tasker import DootTasker
from doot.utils.task_namer import task_namer as namer
import tomler
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

##-- data
data_path       = resources.files("doot.__templates")
toml_template   = data_path / "basic_toml"
dooter_template = data_path / "dooter"
##-- end data

# Global, single points of truth:
__version__ : Final         = "0.2.0"
config      : tomler.Tomler = None # doot config
locs        : DootLocData   = None # registered locations
args        : tomler.Tomler = None # parsed arg access


def setup(targets=None, prefix=None) -> tupl[Tomler, DootLocData]:
    global config, locs
    targets = targets or constants.default_load_targets
    logging.debug("Loading Doot Config, version: %s targets: %s", __version__, targets)
    if config is not None:
        raise Exception("Setup called even though doot is already set up")

    if not all([isinstance(x, pl.Path) for x in targets]):
        raise TypeError("Doot Config Targets should be pathlib.Path's")

    if not any([x.exists() for x in targets]):
        raise FileNotFoundError("No Doot data found")

    config, locs = setup_agnostic(*targets)

    for x in prefix.split("."):
        config = getattr(config, x)

    return config, locs

def setup_agnostic(*paths):
    config = tomler.load(*paths)
    locs   = DootLocData(files=config.flatten_on().files(wrapper=dict),
                         **config.flatten_on().directories(wrapper=dict))

    # TODO move to config loader
    # # Done like this to avoid recursive imports
    DootTasker.set_defaults(config)
    DootLocData.set_defaults(config)
    return config, locs

def setup_py(path):
    raise DeprecationWarning()
    logging.debug("Found: pyproject.toml, using project.name as src location")
    pyproject = tomler.load(path)
    if config.any_of((None,)).directories.src() is None:
        locs.update(src=pyproject.project.name)

    if not pyproject.on_fail(None).tool.doot():
        return None

    return pyproject.tool.doot
