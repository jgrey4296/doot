##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doit.tools import Interactive

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils.task_group import TaskGroup
from doot.utils.toml_accessor import TomlAccessError

##-- end imports
# https://doc.rust-lang.org/cargo/index.html

def task_cargo_build(profile="debug"):
    """
    Build rust binary
    """
    try:
        bin_file = data_toml.bin[0].name
    except TomlAccessError:
        bin_file = data_toml.package.name

    return {
        "basename" : f"cargo::build.{profile}",
        "actions" : ["cargo build --{selection}"],
        "targets" : [ f"{build_dir}/{profile}/{bin_file}" ],
        "file_dep" : ["Cargo.toml"],
        "params" : [
            { "name"    : "selection",
              "short"   : "s",
              "type"    : str,
              "default" : "bins",
            },
            { "name"    : "profile",
              "short"   : "p",
              "type"    : str,
              "choice"  : [("debug", ""),
                          ("release", "") ],
              "default" : f"{profile}",
            }
        ]
    }

def task_cargo_build_release():
    return task_cargo_build(profile="release")

def task_cargo_install():
    """
    install a rust binary
    """
    return {
        "basename" : "cargo::install",
        "actions"  : ["cargo install"],
        "file_dep" : ["Cargo.toml"],
    }

def task_cargo_test():
    """
    run rust tests
    """
    return {
        "basename" : "cargo::test",
        "actions"  : ["cargo test"],
        "file_dep" : ["Cargo.toml"],
    }

def task_cargo_run():
    """
    run a rust binary
    """
    return {
        "basename" : "cargo::run",
        "actions" : ["cargo run"],
        "file_dep" : ["Cargo.toml"],
        "task_dep" : ["_checkdir::build" ],
    }

def task_cargo_doc():
    """
    build rust docs
    """
    return {
        "basename" : "cargo::doc",
        "actions" : ["cargo doc"],
        "file_dep" : ["Cargo.toml"],
    }

def task_cargo_clean():
    """
    clean the rust project
    """
    return {
        "basename" : "cargo::clean",
        "actions"  : ["cargo clean"],
        "file_dep" : ["Cargo.toml"],
    }


def task_cargo_check():
    """
    lint the rust project
    """
    return {
        "basename" : "cargo::check",
        "actions"  : ["cargo check"],
        "file_dep" : "Cargo.toml",
    }

def task_cargo_update():
    """
    update rust and dependencies
    """
    return {
        "basename" : "cargo::update",
        "actions"  : ["rustup update", "cargo update"],
        "file_dep" : ["Cargo.toml"],
    }

def task_rustup_show():
    """
    show available toolchains
    """
    return {
        "basename" : "cargo::toolchain",
        "actions"  : ["rustup show"],
        "file_dep" : "Cargo.toml",
    }


def task_cargo_rename_binary(profile="release"):
    """
    rename the produced rust binary on mac os,
    for rust-py interaction
    """

    lib_file = f"{build_dir}/{profile}/lib{data_toml.package.name}.dylib"
    shared_file = f"{build_dir}/{profile}/{data_toml.package.name}.so"
    cmd = f"cp {lib_file} {shared_file}"

    return {
        "basename" : f"cargo::rename.{profile}",
        "actions"  : [cmd],
        "file_dep" : ["Cargo.toml", lib_file],
        "task_dep" : ["_checkdir::build" ],
    }

def task_cargo_rename_debug_binary():
    return task_cargo_rename_binary(profile="debug")


def task_cargo_help():
    """ Open a browse to the rust book """
    return {
        "basename" : "cargo::rust.help",
        "actions" : ["browse {url}"],
        "file_dep" : ["Cargo.toml"],
        "params" : [ {"name" : "url",
                      "type" : str,
                      "default" : "https://doc.rust-lang.org/book/title-page.html"
                      }
                    ],
    }


def task_cargo_debug():
    """
    Start lldb on the debug build of the rust binary
    """
    try:
        bin_file = data_toml.bin[0].name
    except TomlAccessError:
        bin_file = data_toml.package.name
    
    return {
        "actions"  : [Interactive(f"lldb {build_dir}/debug/{bin_file}")],
        "file_dep" : ["Cargo.toml", f"{build_dir}/debug/{bin_file}"],
        "task_dep" : [ "_checkdir::build" ],
    }

def task_cargo_version():
    return {
        "actions" : ["cargo --version", "rustup --version"],
        "file_dep" : ["Cargo.toml"],
        "verbosity" : 2,
    }


