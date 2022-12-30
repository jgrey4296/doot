##-- imports
from __future__ import annotations

from functools import partial
import pathlib as pl
import shutil
from doit.action import CmdAction

from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd, regain_focus, ForceCmd
from doot.utils import globber

##-- end imports
# https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html


class GodotCheckTask(globber.FileGlobberMulti):
    """
    Lint all gd scripts in the project
    """
    def __init__(self, srcs:list[pl.Path]):
        super().__init__("godot::check", [".gd"], srcs, rec=True)
        self.failures = set()

    def setup_detail(self, task):
        task.update({
            "actions" : [self.reset_failures],
        })
        return task

    def teardown_detail(self, task):
        task.update({
            "actions" : [self.report_failures],
            "verbosity" : 2,
                    })
        return task

    def subtask_detail(self, fpath, task):
        task.update({"actions"   : [
            ForceCmd(self.build_check, shell=False, handler=partial(self.handle_failure, fpath)),
        ],
                     "file_dep"  : [ fpath ],
                     "uptodate" : [False],
                     })
        return task

    def build_check(self, dependencies):
        return ["godot", "--no-window", "--check-only", "--script", *dependencies]

    def handle_failure(self, fpath, result):
        print("Errors Found in: ", fpath)
        self.failures.add(fpath)
        return None

    def report_failures(self):
        if not bool(self.failures):
            return

        print("==========")
        print("Failures Reported In:")
        for fail in self.failures:
            print("- ", fail)
        print("==========")
        return False

    def reset_failures(self):
        self.failures = set()

class GodotRunScene(globber.FileGlobberSingle):
    """
    Globber to allow easy running of scenes
    """

    def __init__(self, srcs:list[pl.Path]):
        super().__init__("godot::run:scene", [".tscn"], srcs, rec=True)

    def top_detail(self, task:dict):
        task.update({
            "actions" : [CmdAction(self.run_scene_with_arg, shell=False) ],
            "params" : [{ "name"    : "target",
                          "short"   : "t",
                          "type"    : str,
                          "default" : "",
                         },
                        { "name"    : "debug",
                          "short"   : "d",
                          "type"    : bool,
                          "default" : False,
                         },
                        ],
        })
        return task

    def subtask_detail(self, fpath, task):
        task.update({
            "file_dep" : [fpath],
            "params"   : [{ "name"    : "debug",
                            "short"   : "d",
                            "type"    : bool,
                            "default" : False,
                           },
                          ],
            "uptodate" : [False],
        })
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


class GodotRun:
    """
    Run a godot script, with debugging or without
    """

    def __init__(self, build_dir, target):
        self.create_doit_tasks = self.build
        self.build_dir         = build_dir
        self.target            = target

    def params(self):
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

    def build(self):
        return { "basename" : "godot::run",
                 "actions"  : [ CmdAction(self.run_cmd, shell=False),
                                regain_focus(),
                               ],
                 "params"   : self.params(),
                 "verbosity" : 2,
                }

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

class GodotBuild:
    """
    build a godot project
    """

    def __init__(self, build_dir):
        self.create_doit_tasks = self.build
        self.build_dir         = build_dir

    def build(self):
        return { "basename" : "godot::build",
                 "actions"  : [CmdAction(self.cmd_builder, shell=False) ],
                 "targets"  : [ self.build_dir / "build.dmg" ],
                 "file_dep" : ["export_presets.cfg"],
                 "params"   : [
                     { "name"    : "build_target",
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
    return { "basename": "godot::test",
             "actions": []
            }


def task_newscene():
    return {
        "basename" : "godot::new:scene",
        "actions" : [],
        "params" : [
            { "name"    : "name",
              "short"   : "n",
              "type"    : str,
              "default" : "default"
             }
        ],
        }
