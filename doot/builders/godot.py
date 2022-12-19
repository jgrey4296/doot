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
    return { "basename": "godot::check"
             "actions": []
            }

def task_godot_version():
    return { "basename": "godot::version"
             "actions": []
            }

def task_godot_run():
    return { "basename": "godot::run"
             "actions": []
            }

def task_godot_test():
    return { "basename": "godot::test"
             "actions": []
            }

def task_godot_debug():
    return { "basename": "godot::debug"
             "actions": []
            }

def task_godot_script():
    return { "basename": "godot::script"
             "actions": []
            }

def task_godot_build():
    # export
    return { "basename": "godot::build"
             "actions": []
            }
