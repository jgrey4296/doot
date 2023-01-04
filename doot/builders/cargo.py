##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from sys import platform

from doit.tools import Interactive

from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.task_group import TaskGroup
from doot.utils.toml_access import TomlAccessError

##-- end imports
# https://doc.rust-lang.org/cargo/index.html

def task_cargo_build(dirs:DootLocData, target:tuple[str, str], profile="debug", data:pl.Path|str="Cargo.toml"):
    """
    Build rust binary target, using a tuple (type, name)
    eg: (bin, main) or (lib, mylib)
    """
    base_name = f"cargo::build.{profile}.{target[1]}"

    def cmd_builder(selection, task):
        return ["cargo", "build", f"--{target[0]}", target[1], "--profile", profile]

    return {
        "basename" : base_name,
        "actions"  : [ CmdAction(cmd_builder, shell=False) ],
        "targets"  : [ dirs.build  / profile / target[1] ],
        "file_dep" : [ data ],
        ]
    }

def task_cargo_install(profile="debug", data:pl.Path|str="Cargo.toml"):
    """
    install a rust binary
    """
    return {
        "basename" : f"cargo::install.{profile}.{target[1]}",
        "actions"  : [ CmdAction(["cargo", "install", "--profile", profile ], shell=False) ],
        "file_dep" : [ data ],
    }

def task_cargo_test(profile="debug", data:pl.Path|str="Cargo.toml"):
    """
    run rust tests
    """
    return {
        "basename" : f"cargo::test.{profile}",
        "actions"  : [CmdAction(["cargo", "test", "--profile", profile, "--workspace"], shell=False) ],
        "file_dep" : [ data ],
    }

def task_cargo_run(target:tuple[str, str], profile="debug", data:pl.Path|str="Cargo.toml"):
    """
    run a rust binary
    """
    return {
        "basename" : "cargo::run.{profile}",
        "actions"  : [CmdAction(["cargo", "run", f"--{target[0]}", target[1]], shell=False)],
        "file_dep" : [data],
        "task_dep" : ["_checkdir::build" ],
    }

def task_cargo_doc(data:pl.Path|str="Cargo.toml"):
    """
    build rust docs
    """
    return {
        "basename" : "cargo::doc",
        "actions"  : [CmdAction(["cargo", "doc"], shell=False) ],
        "file_dep" : [data],
    }

def task_cargo_clean(data:pl.Path|str="Cargo.toml"):
    """
    clean the rust project
    """
    return {
        "basename" : "cargo::clean",
        "actions"  : [CmdAction(["cargo", "clean"], shell=False) ],
        "file_dep" : [ data ],
    }


def task_cargo_check(data:pl.Path|str="Cargo.toml"):
    """
    lint the rust project
    """
    return {
        "basename" : "cargo::check",
        "actions"  : [ CmdAction(["cargo", "check", "--workspace"], shell=False) ],
        "file_dep" : [data],
    }

def task_cargo_update(data:pl.Path|str="Cargo.toml"):
    """
    update rust and dependencies
    """
    return {
        "basename" : "cargo::update",
        "actions"  : [CmdAction(["rustup", "update"], shell=False),
                      CmdAction(["cargo", "update"], shell=False),
                      ],
        "file_dep" : [data],
    }

def task_cargo_mac_lib(dirs:DootLocData, package:str, profile="debug", data:pl.Path|str="Cargo.toml"):
    """
    rename the produced rust binary on mac os,
    for rust-py interaction
    """
    if platform != "darwin":
        return None

    lib_file    = dirs.build  / profile / f"lib{package}.dylib"
    shared_file = dirs.build / profile / f"{package}.so"

    def rename_target(task):
        lib_file.rename(shared_file)

    cmd = f"cp {lib_file} {shared_file}"

    yield {
        "basename" : f"cargo::mac.{profile}.lib",
        "actions"  : [ rename_target ],
        "target"   : [ shared_file ],
        "file_dep" : [ data, , lib_file],
        "task_dep" : [ f"_cargo::build.{profile}.lib" ],
    }

    build_lib = task_cargo_build(dirs.build, target=("lib", fname), profile=profile, data=data)
    build_lib['basename'] = f"_cargo::build.{profile}.lib"
    yield build_lib



def task_cargo_debug(dirs:DootLocData, target:tuple[str, str], data:pl.Path|str="Cargo.toml"):
    """
    Start lldb on the debug build of the rust binary
    """
    assert(target[0] == "bin")
    return {
        "basename" : f"cargo::debug.{target[1]}"
        "actions"  : [Interactive(["lldb", dirs.build / "debug" / target[1] ], shell=False)],
        "file_dep" : [ data, dirs.build / "debug" / target[1] ],
        "task_dep" : [f"cargo::build.debug.{target[1]}"],
    }

def task_cargo_version(data:pl.Path|str="Cargo.toml"):
    return {
        "basename" : "cargo::version",
        "actions" : [CmdAction(["cargo", "--version"], shell=False),
                     CmdAction(["rustup", "--version"], shell=False),
                     CmdAction(["rustup", "show"], shell=False),
                     ],
        "file_dep" : [data],
        "verbosity" : 2,
    }


def task_cargo_report(data:pl.Path|str="Cargo.toml"):
    return {
        "basename"  : "cargo::report",
        "actions"   : [CmdAction(["cargo", "report", "future-incompat"], shell=False) ],
        "file_dep"  : [data],
        "verbosity" : 2,
    }
