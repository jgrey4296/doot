##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

from doot.utils.task_group import TaskGroup
##-- end imports
# https://pip.pypa.io/en/stable/cli/
# TODO add increment version tasks, plus update __init__.py
# TODO install dependencies
temp_dir  = build_dir / "temp"
pip_dir   = build_dir / "pip"
wheel_dir = build_dir / "wheel"


editlib   = CmdTask("pip", "install", "--no-input", "--editable", ".", task_dep=[ "_checkdir::build"  ], basename="pip::local")
install   = CmdTask("pip", "install", "--no-input", "--src", temp_dir, task_dep=[ "_checkdir::build" ], basename="pip::install")
srcbuild  = CmdTask("pip", "install", "--no-input", "--upgrade", "--target", pip_dir, "--src",  temp_dir, ".",
                    task_dep=[ "_checkdir::build" ], basename="pip::build.src")

wheel     = CmdTask("pip", "wheel", "--no-input", "--wheel-dir", wheel_dir, "--use-pep517", "--src", temp_dir, ".",
                    task_dep=[ "_checkdir::build" ], basename="pip::build wheel")
uninstall = CmdTask("pip", "uninstall", "-y", data_toml.project.name, basename="pip::uninstall")

version   = CmdTask("pip", "--version", verbosity=2, basename="pip::version")

def pip_requirements() -> dict:
    """:: generate requirements.txt """
    target = "requirements.txt"
    cmd  = "pip"
    args1 = ["freeze", "--all", "--exclude-editable",
             "-r", "requirements.txt", ">", target]
    args2 = ["list", "--format=freeze", ">", target]

    return {
        'basename': "pip::requirements",
        "actions" : [
            build_cmd(cmd, args1),
            build_cmd(cmd, args2),
        ],
        "targets" : [ target ],
        "clean"   : True,
    }
