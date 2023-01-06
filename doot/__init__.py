#!/usr/bin/env python3
##-- imports
import pathlib as pl
from importlib import resources

from doot.utils.locdata import DootLocData
from doot.utils.toml_access import TomlAccess, TomlAccessError
##-- end imports

##-- data
data_path = resources.files("doot.__templates")
toml_template = data_path / "basic_toml"
dooter_template = data_path / "dooter"
##-- end data


config     : TomlAccess = None

locs       : DootLocData   = None

default_dooter      = pl.Path("dooter.py")
default_py          = pl.Path("pyproject.toml")
default_rust        = pl.Path("Cargo.toml")
default_rust_config = pl.Path("./.cargo/config/toml")
default_agnostic    = pl.Path("doot.toml")

def setup():
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
    elif default_rust.exists():
        return setup_rust()

def setup_agnostic(path=default_agnostic):
    global config, locs
    config     = TomlAccess.load(path)

    locs = DootLocData(None,
                       _src=config.or_get(None).tool.doot.directories.src(),
                       _build=config.or_get(None).tool.doot.directories.build(),
                       _codegen=config.or_get(None).tool.doot.directories.codegen(),
                       _temp=config.or_get(None).tool.doot.directories.temp(),
                       _docs=config.or_get(None).tool.doot.directories.docs(),
                       _data=config.or_get(None).tool.doot.directories.data(),
                       )

def setup_py(path=default_py):
    # print("Setting up python")
    pyproject = TomlAccess.load(path)
    locs._src = pyproject.project.name
    pass

def setup_rust(path=default_rust, config_path=default_rust_config):
    cargo        = TomlAccess.load(path)
    cargo_config = TomlAccess.load(config_path)

    locs._src = cargo.package.name
    locs._build = cargo_config.build.target_dir
