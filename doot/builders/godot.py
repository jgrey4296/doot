##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports
# https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html


def task_godot_check():
    """
    Lint all gd scripts in the project
    """
    for script in pl.Path().rglob("*.gd"):
        return { "basename": "godot::check",
                 "actions": [ "godot --no-window --check-only --script {dependencies}"],
                 "file_dep" : [ script ],
                }

def task_godot_version():
    return { "basename": "godot::version",
             "actions": ["godot --version"]
            }

def task_godot_run():
    """
    Run a godot script or scene, with debugging or without
    """
    def run_cmd(target, debug):
        ext = pl.Path(target).suffix
        args = []
        if debug:
            args.append("-d")

        match ext:
            case ".tscn":
                args.append(target)
            case ".gd":
                args.append("--no-window")
                args.append("--script")
                args.append(target)

        return "godot " + " ".join(args)

    return { "basename": "godot::run",
             "actions": ["godot {debug} {scene}"],
             "params" : [
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
             ],
            }

def task_godot_test():
    return { "basename": "godot::test",
             "actions": []
            }

def task_godot_build():
    """
    build a godot project
    """
    return { "basename": "godot::build",
             "actions": ["godot --no-window --{type} {target}" + f"{build_dir}/build.dmg"],
             "params" : [
                 { "name"    : "target",
                   "short"   : "t",
                   "type"    : str,
                   "default" : "osx",
                   "choices" : [("Mac OSX", ""),
                                ("Android", ""),
                                ],
                  },
                 { "name"    : "type",
                   "long"    : "type",
                   "type"    : str,
                   "default" : "export",
                   "choices" : [ ("export", ""),
                                 ("export-debug", "")
                                ]
                  },
             ]
            }
