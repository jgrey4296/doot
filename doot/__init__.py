#!/usr/bin/env python3
##-- imports
import pathlib as pl
from doot.utils.toml_access import TomlAccess, TomlAccessError
from doot.files.checkdir import CheckDir
##-- end imports

data_toml   = None
config_toml = None
src_dir     = None
doc_dir     = None
temp_dir    = None
gen_dir     = None
build_dir   = None

def setup_py(path="pyproject.toml"):
    global data_toml, src_dir, gen_dir, build_dir, check_build, config_toml, temp_dir, doc_dir
    data_toml   = TomlAccess.load(path)
    config_toml = data_toml
    src_dir     = pl.Path(data_toml.project.name)
    doc_dir     = pl.Path(data_toml.or_get("docs").tool.doot.doc_dir())
    temp_dir    = pl.Path(data_toml.or_get(".temp").tool.doot.temp_dir())
    gen_dir     = src_dir / "_codegen"
    build_dir   = pl.Path(data_toml.or_get("build").tool.doit.build_dir())
    CheckDir(paths=[temp_dir], name="temp", meta={"force_clean":True})
    CheckDir(paths=[build_dir, gen_dir, doc_dir], name="build", task_dep=["_checkdir::temp"])
    return data_toml

def setup_rust(path="Cargo.toml", config="./.cargo/config/toml"):
    global data_toml, src_dir, gen_dir, build_dir, check_build, config_toml, temp_dir, doc_dir
    data_toml   = TomlAccess.load(path)
    config_toml = TomlAccess.load(config)
    src_dir     = pl.Path(data_toml.package.name)
    doc_dir     = pl.Path(data_toml.or_get("docs").tool.doot.doc_dir())
    temp_dir    = pl.Path(data_toml.or_get(".temp").tool.doot.temp_dir())
    gen_dir     = src_dir / "_codegen"
    build_dir   = pl.Path(config_toml.build.target_dir)
    CheckDir(paths=[temp_dir], name="temp", meta={"force_clean":True})
    CheckDir(paths=[build_dir, gen_dir, doc_dir], name="build", task_dep=["_checkdir::temp"])
    return data_toml

def setup_agnostic(path="doot.toml"):
    global data_toml, src_dir, gen_dir, build_dir, check_build, config_toml, temp_dir, doc_dir
    data_toml   = TomlAccess.load(path)
    config_toml = data_toml
    src_dir     = pl.Path(data_toml.project.name)
    try:
        data_toml.tool.doot.codegen
        gen_dir     = src_dir / "_codegen"
        CheckDir(paths=[gen_dir], name="codegen", task_dep=[])
    except TomlAccessError:
        pass

    try:
        doc_dir     = pl.Path(data_toml.tool.doot.doc_dir)
        CheckDir(paths=[doc_dir], name="doc", task_dep=[])
    except TomlAccessError:
        pass

    try:
        temp_dir    = pl.Path(data_toml.tool.doot.temp_dir)
        CheckDir(paths=[temp_dir], name="temp", meta={"force_clean":True})
    except TomlAccessError:
        pass

    try:
        build_dir   = pl.Path(data_toml.tool.doit.build_dir)
        CheckDir(paths=[build_dir], name="build", task_dep=[])
    except TomlAccessError:
        pass
    return data_toml


def task_py_init():
    """
    :: configure a python project
    """

    return {
        "actions"     : [],
    }



def task_cargo_init():
    """
    create a cargo package, and set then customise it with building to 'build',
    and setting to use nightly features
    """
    mk_config_dir = "mkdir ./.cargo"
    set_build_dir = """echo "[build]\ntarget-dir = "build"\n" >> ./.cargo/config.toml"""
    add_features  = """echo -e "cargo-features = [{features}]\n\n" | cat - Cargo.toml > cargo_amended"""
    replace_cargo = "mv cargo_amended Cargo.toml"
    return {
        "basename" : "cargo::init",
        "actions"  : ["cargo init", mk_config_dir, set_build_dir, add_features, replace_cargo],
        "targets"  : ["Cargo.toml"],
        "params" : [ { "name" : "features",
                       "type" : str,
                       "default" : '"profile-rustflags"',
                      },
                    ]
    }


def task_gradle_init():
    """
    :: configure a gradle project
    """

    return {
        "actions" : [],
        "targets" : ["build.gradle.kts",
                     "logging.properties"],
    }

def task_sphinx_init():
    return {
        "actions" : [],
        "targets" : [],
    }

def task_jekyll_init():
    return {
        "actions" : [],
        "targets" : [],
    }

def task_godot_init():
    return {
        "actions" : [],
        "targets" : [],
    }

def task_latex_init():
    return {
        "actions" : [],
        "targets" : [],
    }
