##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

from doot.utils.task_group import TaskGroup
##-- end imports
# https://pip.pypa.io/en/stable/cli/
# TODO add increment version tasks, plus update __init__.py
# TODO install dependencies



editlib   = CmdTask("pip", "install", "-e", ".", task_dep=[ "checkdir::build"  ], basename="pip.local")
install   = CmdTask("pip", "install", "--use-feature=in-tree-build", "--src", build_dir / "pip_temp", task_dep=[ "checkdir::build" ], basename="pip.install")
wheel     = CmdTask("pip", "wheel", "--use-feature=in-tree-build", "-w", build_dir / "wheel", "--use-pep517", "--src", build_dir / "pip_temp", ".",
                    task_dep=[ "checkdir::build" ], basename="pip.build wheel")
srcbuild  = CmdTask("pip", "install", "--use-feature=in-tree-build", "-t", build_dir / "pip_src", "--src",  build_dir / "pip_temp", "-U",  ".",
                    task_dep=[ "checkdir::build" ], basename="pip.build.src")
uninstall = CmdTask("pip", "uninstall", "-y", datatoml.project.name, basename="pip.uninstall")

version   = CmdTask("pip", "--version", verbosity=2, basename="pip.version")

def pip_requirements() -> dict:
    """:: generate requirements.txt """
    target = "requirements.txt"
    cmd  = "pip"
    args1 = ["freeze", "--all", "--exclude-editable",
             "-r", "requirements.txt", ">", target]
    args2 = ["list", "--format=freeze", ">", target]

    return {
        'basename': "requirements.txt",
        "actions" : [
            build_cmd(cmd, args1),
            build_cmd(cmd, args2),
        ],
        "targets" : [ target ],
        "clean"   : True,
    }
