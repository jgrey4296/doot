##-- imports
from __future__ import annotations

from functools import partial
import pathlib as pl
import shutil
from doit.action import CmdAction

from doot.utils.general import regain_focus, ForceCmd
from doot.utils import globber
from doot.utils.tasker import DootTasker

##-- end imports
# https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html

class GodotRunScene(globber.HeadlessFileGlobber):
    """
    ([root]) Globber to allow easy running of scenes
    """

    def __init__(self, name="godot::run:scene", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dir.root], exts=[".tscn"], rec=rec)

    def set_params(self):
        return [{ "name"    : "target",
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
            "actions" : [CmdAction(self.run_scene_with_arg, shell=False) ],
            "actions" : self.set_params(),
        })
        return task

    def subtask_detail(self, task, fpath=None):
        task.update({
            "file_dep" : [fpath],
        })
        task['actions'] += self.subtask_actions(fpath)
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction(self.run_scene, shell=False) ]

    def run_scene(self, dependencies, debug):
        return self.run_scene_with_arg(dependencies[0], debug)

    def run_scene_with_arg(self, target, debug):
        args = ["godot"]
        if debug:
            args.append("-d")

        args.append(target)
        return args


class GodotRunScript(globber.EagerFileGlobber):
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
              "default" : self.target,
             },
            { "name"    : "debug",
              "short"   : "d",
              "type"    : bool,
              "default" : False,
             },
        ]

    def subtask_detail(self, task, fpath=None):
        task.update({ "verbosity" : 2,})
        task['actions'] += self.subtask_actions(fpath)
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction(partial(self.run_cmd, fpath), shell=False), regain_focus() ]

    def run_cmd(self, target, debug):
        if not bool(target):
            return ["echo", "No Target Specified"]
        if not pl.Path(target).exists():
            return ["echo", "Target Doesn't Exist: ", target]
        args = ["godot"]
        if debug:
            args.append("-d")

        args.append("--no-window")
        args.append("--script")
        args.append(target)

        return args

class GodotBuild(DootTasker):
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
                 "actions"  : [ CmdAction(self.cmd_builder, shell=False) ],
                 "targets"  : [ self.build_dir / "build.dmg" ],
                 "file_dep" : [ "export_presets.cfg" ],
                 "clean"    : True,
                 ]
                }

    def cmd_builder(self, build_type, build_target, targets):
        return ["godot", "--no-window", f"--{build_type}",  build_target, targets[0] ]

def task_godot_version():
    return { "basename"  : "godot::version",
             "actions"   : [
                 ForceCmd(["godot", "--version"], shell=False),
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
        return ["touch", (dirs.extra['scenes'] / name).with_suffix(".tscn") ]

    return {
        "basename" : "godot::new:scene",
        "actions" : [ CmdAction(mkscene, shell=False) ],
        "set_params" : [
            { "name"    : "name",
              "short"   : "n",
              "type"    : str,
              "default" : "default"
             }
        ],
        }
