##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils.task_group import TaskGroup

##-- end imports


def task_cargo_check():
    return {
        "actions" : [],
        "file_dep" : "Cargo.toml",
    }

def task_cargo_init():
    return {
        "actions" : [],
        "file_dep" : "Cargo.toml",
    }

def task_rustup():
    return {
        "actions" : [],
        "file_dep" : "Cargo.toml",
    }


def task_cargo_rename_binary():
    """ rename the produced rust binary on mac os,
    for rust-py interaction

	cp ${BUILD}/${TARGET}/lib${NAME}.dylib ${BUILD}/${NAME}.so
    """
    return {
        "actions" : [],
        "file_dep" : "Cargo.toml",
    }


def task_cargo_docs():
    return {
        "actions" : [],
        "file_dep" : "Cargo.toml",
    }


def task_cargo_help():
    # https://doc.rust-lang.org/book/title-page.html
    return {
        "actions" : [],
        "file_dep" : "Cargo.toml",
    }


def task_cargo_debug():
    return {
        "actions" : [],
        "file_dep" : "Cargo.toml",
    }


def task_cargo_release():
    return {
        "actions" : [],
        "file_dep" : "Cargo.toml",
    }


def task_cargo_test():
    return {
        "actions" : [],
        "file_dep" : "Cargo.toml",
    }


def task_cargo_version():
    return {
        "actions" : [],
        "file_dep" : "Cargo.toml",
    }


