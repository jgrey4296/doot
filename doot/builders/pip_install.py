##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports
# https://pip.pypa.io/en/stable/cli/
# TODO add increment version tasks, plus update __init__.py
# TODO install dependencies

pip_editlib   = CmdTask("pip", "install", "-e", ".", task_dep=[ "CheckDir::build"  ])
pip_install   = CmdTask("pip", "install", "--use-feature=in-tree-build", "--src", build_dir / "pip_temp", task_dep=[ "CheckDir::build" ])
pip_wheel     = CmdTask("pip", "wheel", "--use-feature=in-tree-build", "-w", build_dir / "wheel", "--use-pep517", "--src", build_dir / "pip_temp", ".", task_dep=[ "CheckDir::build" ])
pip_srcbuild  = CmdTask("pip", "install", "--use-feature=in-tree-build", "-t", build_dir / "pip_src", "--src",  build_dir / "pip_temp", "-U",  ".", task_dep=[ "CheckDir::build" ])
pip_uninstall = CmdTask("pip", "uninstall", "-y", datatoml['project']['name'])


def task_pip_requirements() -> dict:
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

def task_pip_version():
    pass
