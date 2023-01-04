#!/usr/bin/env python3
##-- imports
import pathlib as pl
from doot.utils.toml_access import TomlAccess, TomlAccessError
from doot.files.checkdir import CheckDir
from doot.utils.dir_data import DootDirs
##-- end imports

data_toml   : TomlAccess = None
config_toml : TomlAccess = None
doot_dirs   : DootDirs   = None

default_py       = pl.Path("pyproject.toml")
default_rust     = pl.Path("Cargo.toml")
default_agnostic = pl.Path("doot.toml")

def setup():
    if default_py.exists():
        return setup_py()
    elif default_rust.exists():
        return setup_rust()
    elif default_agnostic.exists():
        return setup_agnostic()
    else:
        raise Exception("Not Config Data Found")


def setup_py(path="pyproject.toml"):
    global data_toml, config_toml, doot_dirs
    data_toml   = TomlAccess.load(path)
    config_toml = data_toml

    doot_dirs = DootDirs(None,
                         _build=data_toml.or_get("build").tool.doit.directories.build(),
                         _src=data_toml.project.name,
                         _codegen=data_toml.or_get("_codegen").tool.doot.directories.codegen(),
                         _temp=data_toml.or_get(".temp").tool.doot.directories.temp(),
                         _docs=data_toml.or_get("docs").tool.doot.directories.docs(),
                         _data=data_toml.or_get("data").tool.doot.directories.data(),
                         )
    return data_toml, doot_dirs

def setup_rust(path="Cargo.toml", config="./.cargo/config/toml"):
    global data_toml, config_toml, doot_dirs
    data_toml   = TomlAccess.load(path)
    config_toml = TomlAccess.load(config)


    doot_dirs = DootDirs("",
                         _src=data_toml.package.name,
                         _build=config_toml.or_get("build").build.target_dir(),
                         _codegen=data_toml.or_get("_codegen").tool.doot.directories.codegen(),
                         _temp=data_toml.or_get(".temp").tool.doot.directories.temp(),
                         _docs=data_toml.or_get("docs").tool.doot.directories.docs(),
                         _data=data_toml.or_get("data").tool.doot.directories.data(),
                         )
    return data_toml, doot_dirs

def setup_agnostic(path="doot.toml"):
    global data_toml, config_toml, doot_dirs
    data_toml   = TomlAccess.load(path)
    config_toml = data_toml

    doot_dirs = DootDirs("",
                         _build=data_toml.or_get("build").tool.doit.directories.build(),
                         _src=data_toml.project.name,
                         _codegen=data_toml.or_get("_codegen").tool.doot.directories.codegen(),
                         _temp=data_toml.or_get(".temp").tool.doot.directories.temp(),
                         _docs=data_toml.or_get("docs").tool.doot.directories.docs(),
                         _data=data_toml.or_get("data").tool.doot.directories.data(),
                         )
    return data_toml, doot_dirs
