#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging


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
    def make_config():
        pl.Path("./.cargo").mkdir()

    def set_build_dir():
        pl.Path("./.cargo/config.toml").write_text("\n".join(["[build]",
                                                              "target-dir = \"build\"",
                                                              ]))

    def add_features(features):
        cargo_file = pl.Path("Cargo.toml")
        header     = f"cargo-features = [{features}]\n"
        cargo_text = cargo_file.read_text()
        cargo_file.write_text("\n".join([header, cargo_text]))
    #------
    return {
        "basename" : "cargo::init",
        "actions"  : [CmdAction(["cargo", "init"], shell=False),
                      make_config, set_build_dir, add_features],
        "targets"  : ["Cargo.toml", ".cargo/config.toml"],
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
