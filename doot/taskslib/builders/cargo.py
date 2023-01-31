##-- imports
from __future__ import annotations

from typing import Final
import pathlib as pl
import shutil
import sys

from doit.action import CmdAction
from doit.tools import Interactive

import doot
from doot.task_group import TaskGroup
from tomler import TomlAccessError, Tomler
from doot import tasker, task_mixins

##-- end imports
# https://doc.rust-lang.org/cargo/index.html

cargo  = Tomler.load("Cargo.toml")
config = Tomler.load("./.cargo/config.toml")

build_path    : Final = config.on_fail(str(doot.locs.build)).build.target_dir()
package_name  : Final = cargo.package.name
profiles      : Final = ["release", "debug", "dev"] + cargo.on_fail([]).profile()
binaries      : Final = [x.get('name') for x in  cargo.on_fail([], list).bin()]
lib_path      : Final = cargo.on_fail(None, None|str).lib.path()


class CargoBuild(tasker.DootTasker, task_mixins.ActionsMixin):
    """
    Build rust binary target, using a tuple (type, name)
    eg: (bin, main) or (lib, mylib)
    """

    def __init__(self, name="cargo::build", locs=None):
        super().__init__(name, locs)
        assert(self.locs.build)

    def set_params(self):
        return [
            { "name": "profile", "type": str, "short": "p", "default": "debug", "choices": [(x,"") for x in profiles] },
            { "name": "target",  "type": str, "short": "t", "default": binaries[0], "choices": [(x, "") for x in binaries]},
            { "name": "lib", "type": bool, "short": "l", "default": False},
        ]

    def task_detail(self, task):
        target_dir = self.locs.build / self.args['profile']
        match self.args['lib'], sys.platform:
            case True, "darwin":
                # libraries on mac need to be renamed:
                lib_file     =  f"lib{package_name}.dylib"
                build_target = target_dir / f"{package_name}.so"
                actions      = [ self.cmd(self.lib_build),
                                 (self.move_to, [build_target, target_dir / lib_file ]),
                                ]
            case True, _:
                build_target =  target_dir / f"lib{package_name}.dylib"
                actions      = [ self.cmd(self.lib_build) ]
            case False, _:
                build_target = target_dir / self.args['target']
                actions      = [ self.cmd(self.binary_build) ]

        task.update({
            "actions"  : actions,
            "targets"  : [ build_target ],
        })
        return task

    def binary_build(self):
        return ["cargo", "build", "--bin", self.args['target'], "--profile", self.args['profile']]

    def lib_build(self):
        return ["cargo", "build", "--lib", "--profile", self.args['profile']]

class CargoInstall(tasker.DootTasker, task_mixins.ActionsMixin):

    def __init__(self, name="cargo::install", locs=None):
        super().__init__(name, locs)

    def set_params(self):
        return [
            { "name": "profile", "type": str, "short": "p", "default": "debug", "choices": [(x,"") for x in profiles] },
            { "name": "target",  "type": str, "short": "t", "default": binaries[0], "choices": [(x, "") for x in binaries]},
        ]

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.cmd(self.binary_build) ],
        })
        return task

    def binary_build(self):
        return ["cargo", "install", "--bin", self.args['target'], "--profile", self.args['profile']]

class CargoTest(tasker.DootTasker, task_mixins.ActionsMixin):

    def __init__(self, name="cargo::test", locs=None):
        super().__init__(name, locs)

    def set_params(self):
        return [
            { "name": "profile", "type": str, "short": "p", "default": "debug", "choices": [(x,"") for x in profiles] },
            { "name": "name", "type": str, "short": "n", "default": ""},
            { "name": "no_run", "type": bool, "long": "no-run", "default": False},
        ]

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.cmd(self.test_cmd) ],
            "targets"  : [  ],
        })
        return task

    def test_cmd(self):
        return ["cargo", "test", "--bin", self.args['target'], "--profile", self.args['profile']]

class CargoDocs(tasker.DootTasker, task_mixins.ActionsMixin):

    def __init__(self, name="cargo::docs", locs=None):
        super().__init__(name, locs)

    def set_params(self):
        return [
            {"name": "no-deps", "type": bool, "short": "d", "default": True}
        ]

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.cmd(["cargo", "doc"]) ],
        })
        return task


class CargoRun(tasker.DootTasker, task_mixins.ActionsMixin):

    def __init__(self, name="cargo::run", locs=None):
        super().__init__(name, locs)

    def set_params(self):
        return [
            { "name": "profile", "type": str, "short": "p", "default": "debug", "choices": [(x,"") for x in profiles] },
            { "name": "target",  "type": str, "short": "t", "default": binaries[0], "choices": [(x, "") for x in binaries]},
        ]

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.cmd(["cargo", "run", "--bin", self.args['target'], "--profile", self.args['profile'] ]) ],
        })
        return task

class CargoClean(tasker.DootTasker, task_mixins.ActionsMixin):
    """
    clean the rust project
    """
    def __init__(self, name="cargo::clean", locs=None):
        super().__init__(name, locs)

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.cmd(["cargo", "clean"]) ],
        })
        return task

class CargoCheck(tasker.DootTasker, task_mixins.ActionsMixin):
    """
    run cargo check on the project
    """

    def __init__(self, name="cargo::check", locs=None):
        super().__init__(name, locs)

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.cmd(["cargo", "check", "--workspace"]) ],
        })
        return task

class CargoUpdate(tasker.DootTasker, task_mixins.ActionsMixin):
    """
    update rust and dependencies
    """

    def __init__(self, name="cargo::update", locs=None):
        super().__init__(name, locs)

    def task_detail(self, task):
        task.update({
            "actions"  : [ self.cmd(["rustup", "update"]),
                           self.cmd(["cargo", "update"]),
                          ],
        })
        return task

class CargoDebug(tasker.DootTasker, task_mixins.ActionsMixin):
    """
    Start lldb on the debug build of the rust binary
    """

    def __init__(self, name="cargo::debug", locs=None):
        super().__init__(name, locs)
        assert(self.locs.build)

    def set_params(self):
        return [
            { "name": "target",  "type": str, "short": "t", "default": binaries[0], "choices": [(x, "") for x in binaries]},
        ]

    def task_detail(self, task):
        task.update({
                "actions"  : [ self.interact(["lldb", self.locs.build / "debug" / self.args['target'] ]) ],
                "file_dep" : [ self.locs.build / "debug" / self.args['target'] ],
            })
        return task

def task_cargo_version():
    return {
        "basename" : "cargo::version",
        "actions" : [ task_mixins.ActionsMixin.cmd(None, ["cargo", "--version"]),
                      task_mixins.ActionsMixin.cmd(None, ["rustup", "--version"]),
                      task_mixins.ActionsMixin.cmd(None, ["rustup", "show"]),
                     ],
        "verbosity" : 2,
    }

def task_cargo_report():
    return {
        "basename"  : "cargo::report",
        "actions"   : [ task_mixins.ActionsMixin.cmd(None, ["cargo", "report", "future-incompat"]) ],
        "verbosity" : 2,
    }
