#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
from importlib import resources

from doot.loc_data import DootLocData
from doot.tasker import DootTasker
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

__version__              = "0.0.1"

default_dooter           = pl.Path("dooter.py")

default_py               = pl.Path("pyproject.toml")

default_rust             = pl.Path("Cargo.toml")

default_rust_config      = pl.Path("./.cargo/config.toml")

default_agnostic         = pl.Path("doot.toml")

config     : tomler.Tomler = None
locs       : DootLocData   = None

def setup():
    logging.info("Setting up Doot, version: %s", __version__)
    if config is not None:
        raise Exception("Setup called even though doot is already set up")

    if not default_dooter.exists():
        raise FileNotFoundError("No Dooter found")
    elif default_agnostic.exists():
        setup_agnostic()
    else:
        raise FileNotFoundError("No Config File was found")

    if default_py.exists():
        return setup_py()

def setup_agnostic(path=default_agnostic):
    global config, locs
    config = tomler.load(path)
    locs   = DootLocData(files=config.flatten_on().tool.doot.files(wrapper=lambda x: x.get_table()),
                         **config.flatten_on().tool.doot.directories(wrapper=lambda x: x.get_table()))

    # Done like this to avoid recursive imports
    DootTasker.set_defaults(config)
    DootLocData.set_defaults(config)

def setup_py(path=default_py):
    logging.info("Found: pyproject.toml, using project.name as src location")
    pyproject = tomler.load(path)
    if config.any_of((None,)).tool.doot.directories.src() is None:
        locs.update(src=pyproject.project.name)
