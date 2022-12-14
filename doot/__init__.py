#!/usr/bin/env python3
##-- imports
import pathlib as pl
from doot.utils.toml_accessor import TomlAccessor
from doot.files.checkdir import CheckDir
##-- end imports

datatoml           = None
src_dir, build_dir = None, None
check_build        = None

def setup_py(path="pyproject.toml"):
    global datatoml, src_dir, build_dir, check_build
    datatoml    = TomlAccessor.load(path)
    src_dir     = pl.Path(datatoml.project.name)
    build_dir   = pl.Path(datatoml.tool.doit.build_dir)
    check_build = CheckDir(paths=[build_dir], name="build")
    return datatoml

def setup_rust(path="Cargo.toml"):
    global datatoml, src_dir, build_dir, check_build
    datatoml    = TomlAccessor.load(path)
    src_dir     = pl.Path(datatoml.package.name)
    build_dir   = pl.Path(datatoml.tool.doit.build_dir)
    check_build = CheckDir(paths=[build_dir], name="build")
    return datatoml

def setup_agnostic(path="doot.toml"):
    return setup_py(path)
