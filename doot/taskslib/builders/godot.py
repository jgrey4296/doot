##-- imports
from __future__ import annotations

from functools import partial
import pathlib as pl
import shutil

from doot import globber
from doot.tasker import DootTasker, DootActions

##-- end imports
# https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html


class GodotRunScene(globber.HeadlessFileGlobber, DootActions):
    """
    ([root]) Globber to allow easy running of scenes
    """

    def __init__(self, name="godot::run:scene", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dir.root], exts=[".tscn"], rec=rec)

    def set_params(self):
        return [
            { "name"    : "target",
              "short"   : "t",
              "type"    : str,
              "default" : "",
             },
            { "name"    : "debug",
              "short"   : "d",
              "type"    : bool,
              "default" : False,
             },
        ]

    def task_detail(self, task:dict):
        task.update({
            "actions" : [ self.cmd(self.run_scene_with_arg) ],
        })
        return task

    def subtask_detail(self, task, fpath=None):
        task.update({
            "file_dep" : [fpath],
        })
        task['actions'] += [ self.cmd(self.run_scene) ]
        return task

    def run_scene(self, dependencies):
        return self.run_scene_with_arg(dependencies[0], self.params['debug'])

    def run_scene_with_arg(self):
        args = ["godot"]
        if self.params['debug']:
            args.append("-d")

        args.append(self.params['target'])
        return args

class GodotRunScript(globber.EagerFileGlobber, DootActions):
    """
    ([root]) Run a godot script, with debugging or without
    """

    def __init__(self, name="godot::run", dirs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.root], exts=[".gd"], rec=rec)

    def filter(self, fpath):
        # TODO test script for implementing runnable interface
        return True

    def set_params(self):
        return [
            { "name"    : "target",
              "short"   : "t",
              "type"    : str,
              "default" : "",
             },
            { "name"    : "debug",
              "short"   : "d",
              "type"    : bool,
              "default" : False,
             },
        ]

    def subtask_detail(self, task, fpath=None):
        task.update({ "verbosity" : 2,})
        task['actions'] += [ self.cmd(self.run_cmd, [fpath]),
                             self.regain_focus() ]

        return task

    def run_cmd(self, fpath):
        args = ["godot"]
        if self.params['debug']:
            args.append("-d")

        args.append("--no-window")
        args.append("--script")
        args.append(fpath)

        return args

class GodotBuild(DootTasker, DootActions):
    """
    (-> [build]) build a godot project
    """

    def __init__(self, name="godot::build", dirs:DootLocData=None):
        super().__init__(name, dirs)

    def set_params(self):
        return [ { "name"    : "build_target",
                   "short"   : "t",
                   "type"    : str,
                   "default" : "osx",
                   "choices" : [("Mac OSX", ""),
                                ("Android", ""),
                                ],
                  },
                 { "name"    : "build_type",
                   "long"    : "type",
                   "type"    : str,
                   "default" : "export",
                   "choices" : [ ("export", ""),
                                 ("export-debug", "")
                                ]
                  },
                ]

    def setup_detail(self, task):
        task.update({
            "actions" : [ "echo TODO build template export_presets.cfg"],
            "targets" : ["export_presets.cfg"],
        })
        return task

    def task_detail(self, task):
        return { "basename" : "godot::build",
                 "actions"  : [ self.cmd(self.cmd_builder) ],
                 "targets"  : [ self.build_dir / "build.dmg" ],
                 "file_dep" : [ "export_presets.cfg" ],
                 "clean"    : True,
                }

    def cmd_builder(self, targets):
        return ["godot",
                "--no-window",
                f"--{self.params['build_type']}",
                self.params['build_target'],
                targets[0]
                ]

def task_godot_version():
    return { "basename"  : "godot::version",
             "actions"   : [
                 DootActions.force(None, ["godot", "--version"]),
             ],
             "verbosity" : 2,
            }

def task_godot_test():
    """
    TODO run godot tests
    """
    return { "basename": "godot::test",
             "actions": []
            }

def task_newscene(dirs:DootLocData):
    """
    (-> [scenes])
    """
    assert("scenes" in dirs.extra)

    def mkscene(task, name):
        return [ "touch", (dirs.extra['scenes'] / name).with_suffix(".tscn") ]

    return {
        "basename" : "godot::new:scene",
        "actions" : [ DootActions.cmd(None, mkscene) ],
        "set_params" : [
            { "name"    : "name",
              "short"   : "n",
              "type"    : str,
              "default" : "default"
             }
        ],
        }
