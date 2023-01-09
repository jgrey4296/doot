#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from os import environ
from dataclasses import InitVar, dataclass, field
from importlib.resources import files
from re import Pattern
from string import Template
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

import doot
from doit.action import CmdAction
from doot.utils.tasker import DootTasker

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

##-- data
data_path       = files("doot.__templates")
jekyll_config   = data_path.joinpath("jekyll_config")
jekyll_template = Template(jekyll_config.read_text())
##-- end data


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


class JekyllInit(DootTasker):
    """
    ([src, temp, build, data]) init a new jekyll project if it doesnt exist,
    in the config's src path
    """

    def __init__(self, name="jekyll::init", dirs=None):
        super().__init__(name, dirs)
        self.config_file = self.dirs.root / "jekyll.toml"

    def task_detail(self, task):
        task.update({
            "actions" : [CmdAction(self.init_cmd, shell=False),
                         self.make_config,
                         self.move_data,
                         ],
        })
        return task

    def init_cmd(self):
        project_init = ["jekyll", "new",
                        "--force", "--blank",
                        self.dirs.src,
                        ]
        return project_init

    def make_config(self):
        author = environ['USER'] if 'USER' in environ else "Default"
        includes = [self.dirs.codegen.name, self.dirs.extra['tags'].name]
        config_text = jekyll_template.substitute(author=author,
                                                 src=f'./{self.dirs.temp}',
                                                 dst=f'./{self.dirs.build}',
                                                 includes=f"{includes}",
                                                 )
        self.config_file.write_text(config_text)
        (self.dirs.src / "_config.yml").unlink(),



    def move_data(self):
        for f in self.dirs.src.iterdir():
            if f.is_dir() and f.name[0] != "_":
                f.rename(self.dirs.data / f.name)
