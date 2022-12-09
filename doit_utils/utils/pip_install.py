##-- imports
from __future__ import annotations
import pathlib as pl
import shutil

from doit import create_after
from doit.action import CmdAction
from doit.tools import (Interactive, PythonInteractiveAction, create_folder,
                        set_trace)

try:
    # For py 3.11 onwards:
    import tomllib as toml
except ImportError:
    # Fallback to external package
    import toml
##-- end imports


# TODO set targets to .egg-info, eggs etc

# TODO add increment version tasks, plus update __init__.py

install   = JGCmdTask("pip", "install", "--use-feature=in-tree-build", "--src", build_dir / "pip_temp", task_dep=["_base-dircheck"])
wheel     = JGCmdTask("pip", "wheel", "--use-feature=in-tree-build", "-w", build_dir / "wheel", "--use-pep517", "--src", build_dir / "pip_temp", ".", task_dep=["_base-dircheck"])
editlib   = JGCmdTask("pip", "install", "-e", task_dep=["_base-dircheck"])
srcbuild  = JGCmdTask("pip",  "install", "--use-feature=in-tree-build", "-t", build_dir / "pip_src", "--src",  build_dir / "pip_temp", "-U",  ".", task_dep=["_base-dircheck"])
uninstall = JGCmdTask("pip", "uninstall", "-y", pyproject['project']['name'])


def task_requirements() -> dict:
    """:: generate requirements.txt """
    cmd  = "pip"
    args1 = ["freeze", "--all", "--exclude-editable",
             "-r", "requirements.txt", ">", "requirements.txt"]
    args2 = ["list", "--format=freeze", ">", "requirements.txt"]

    return {
        "actions" : [
            build_cmd(cmd, args1),
            build_cmd(cmd, args2),
        ],
        "targets" : [ "requirements.txt" ],
        "clean"   : True,
    }
