##-- imports
from __future__ import annotations

from typing import Final
import pathlib as pl
import shutil
import sys

import logging as logmod

import doot
from doot.core.task.task_group import TaskGroup
from tomler import TomlAccessError, Tomler
from doot import tasker

##-- end imports
# https://doc.rust-lang.org/cargo/index.html

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doot.mixins.cargo import CargoMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin

cargo  = Tomler.load("Cargo.toml")
config = Tomler.load("./.cargo/config.toml")

build_path    : Final[str]          = config.on_fail(str(doot.locs.build)).build.target_dir()
package_name  : Final[str]          = cargo.package.name
lib_file      : Final[str]          =  f"lib{package_name}.dylib"
so_file       : Final[str]          =  f"{package_name}.so"
profiles      : Final[list]         = ["release", "dev"] + cargo.on_fail([]).profile()
binaries      : Final[list]         = [x.get('name') for x in  cargo.on_fail([], list).bin()]
pyproject_p   : Final[bool]         = pl.Path("pyproject.toml").exists()
targets_lib   : Final[bool]         = cargo.on_fail(False).lib() is not False
install_lib   : Final[None|Pl.Path] = doot.config.on_fail(doot.locs.build).group.rust.lib_install(wrapper=lambda x: pl.Path(x).expanduser().resolve())

def task_cargo_version():
    return {
        "basename" : "cargo::version",
        "actions" : [ CommanderMixin.make_cmd(None, "cargo", "--version"),
                      CommanderMixin.make_cmd(None, "rustup", "--version"),
                      CommanderMixin.make_cmd(None, "rustup", "show"),
                     ],
        "verbosity" : 2,
    }

def task_cargo_report():
    return {
        "basename"  : "cargo::report",
        "actions"   : [ CommanderMixin.make_cmd(None, "cargo", "report", "future-incompat") ],
        "verbosity" : 2,
    }

class CargoBuild(tasker.DootTasker, CommanderMixin, CargoMixin, FilerMixin):
    """
    Build rust binary target, using a tuple (type, name)
    eg: (bin, main) or (lib, mylib)
    """

    def __init__(self, name="cargo::build", locs=None):
        super().__init__(name, locs)
        self.locs.ensure("build", task=name)

    def set_params(self):
        return [
            *self.get_cargo_params(),
            { "name": "lib", "type": bool, "short": "l", "default": targets_lib },
        ]

    def task_detail(self, task):
        target_dir   = self.locs.build / ("debug" if self.args['profile'] == "dev" else "release")

        match self.args['lib']:
            case True:
                # libraries on mac need to be renamed:
                task['targets'].append(target_dir / so_file)
                task['targets'].append(self.locs.temp / so_file)
                task['actions'] = [
                    self.cargo_do("build", "--lib", profile=self.args['profile']),
                    (self.copy_to, [self.locs.temp / lib_file, target_dir / lib_file ], {"fn": "file"}),
                    (self.copy_to, [self.locs.temp / so_file, target_dir / lib_file ],  {"fn": "file"}),
                    ]
            case False, _:
                task['targets'].append(target_dir / self.args['target'])
                task['actions'] = [
                    self.cargo_do("build", bin=self.args['target'], profile=self.args['profile'])
                ]

        return task

class CargoInstall(tasker.DootTasker, CommanderMixin, CargoMixin, FilerMixin):

    def __init__(self, name="cargo::install", locs=None):
        super().__init__(name, locs)

    def set_params(self):
        return self.get_cargo_params() + [
            { "name": "lib", "type": bool, "short": "l", "default": targets_lib },
        ]

    def task_detail(self, task):
        if self.args['lib']:
            task['task_dep'] = ["cargo::build"]
            task["actions"] = [
                (self.log, [f"Installing Module to: {install_lib}", logmod.INFO]),
                (self.copy_to, [install_lib / so_file, self.locs.temp / so_file ], {"fn": "file"}),
            ]
        else:
            task["actions"] =[ self.make_cmd(self.binary_build) ],

        return task

    def binary_build(self):
        return ["cargo", "install", "--bin", self.args['target'], "--profile", self.args['profile']]

class CargoTest(tasker.DootTasker, CommanderMixin, CargoMixin):

    def __init__(self, name="cargo::test", locs=None):
        super().__init__(name, locs)

    def set_params(self):
        return [
            { "name": "profile", "type": str, "short": "p", "default": "dev", "choices": [(x,"") for x in profiles] },
            { "name": "name", "type": str, "short": "n", "default": ""},
            { "name": "no_run", "type": bool, "long": "no-run", "default": False},
        ]

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.make_cmd(self.test_cmd) ],
            "targets"  : [  ],
        })
        return task

    def test_cmd(self):
        return ["cargo", "test", "--bin", self.args['target'], "--profile", self.args['profile']]

class CargoDocs(tasker.DootTasker, CommanderMixin, CargoMixin):

    def __init__(self, name="cargo::docs", locs=None):
        super().__init__(name, locs)

    def set_params(self):
        return [
            {"name": "no-deps", "type": bool, "short": "d", "default": True}
        ]

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.make_cmd("cargo", "doc") ],
        })
        return task

class CargoRun(tasker.DootTasker, CommanderMixin, CargoMixin):

    def __init__(self, name="cargo::run", locs=None):
        super().__init__(name, locs)

    def set_params(self):
        return self.get_cargo_params()

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.make_cmd("cargo", "run", "--bin", self.args['target'], "--profile", self.args['profile'] ) ],
        })
        return task

class CargoClean(tasker.DootTasker, CommanderMixin, CargoMixin):
    """
    clean the rust project
    """

    def __init__(self, name="cargo::clean", locs=None):
        super().__init__(name, locs)

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.make_cmd("cargo", "clean") ],
        })
        return task

class CargoCheck(tasker.DootTasker, CommanderMixin, CargoMixin):
    """
    run cargo check on the project
    """

    def __init__(self, name="cargo::check", locs=None):
        super().__init__(name, locs)

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.make_cmd("cargo", "check", "--workspace") ],
        })
        return task

class CargoUpdate(tasker.DootTasker, CommanderMixin, CargoMixin):
    """
    update rust and dependencies
    """

    def __init__(self, name="cargo::update", locs=None):
        super().__init__(name, locs)

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.make_cmd("rustup", "update"),
                           self.make_cmd("cargo", "update"),
                          ],
        })
        return task

class CargoDebug(tasker.DootTasker, CommanderMixin, CargoMixin):
    """
    Start lldb on the debug build of the rust binary
    """

    def __init__(self, name="cargo::debug", locs=None):
        super().__init__(name, locs)
        self.locs.ensure("build", task=name)

    def set_params(self):
        return self.get_cargo_params()

    def task_detail(self, task):
        task.update({
                "actions"  : [ self.make_interact("lldb", self.locs.build / "dev" / self.args['target']) ],
                "file_dep" : [ self.locs.build / "debug" / self.args['target'] ],
            })
        return task
