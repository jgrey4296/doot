##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from doit.action import CmdAction

from doot import data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask

from doot.utils.task_group import TaskGroup
##-- end imports
# https://pip.pypa.io/en/stable/cli/
# TODO add increment version tasks, plus update __init__.py
# TODO install dependencies

prefix = data_toml.or_get("pip").tool.doot.pip.prefix()

def build_tasks(dirs:DootDirs):
    assert("wheel" in dirs.extra)
    assert("sdist" in dirs.extra)
    # Installs:
    editlib   = CmdTask("pip", "install", "--no-input", "--editable", pl.Path(), basename=f"{prefix}::local")
    reglib    = CmdTask("pip", "install", "--no-input", pl.Path(), basename=f"{prefix}::install.regular")
    install   = CmdTask("pip", "install", "--no-input", "--src", dirs.temp, basename=f"{prefix}::install")
    uninstall = CmdTask("pip", "uninstall", "-y", data_toml.project.name, basename=f"{prefix}::uninstall")

    # Builds: TODO add clean
    srcbuild  = CmdTask("pip", "install", "--no-input", "--upgrade", "--target", dirs.extra['sdist'], "--src",  dirs.temp, ".", basename=f"{prefix}::build.src")
    wheel     = CmdTask("pip", "wheel", "--no-input", "--wheel-dir", dirs.extra['wheel'], "--use-pep517", "--src", dirs.temp, ".", basename=f"{prefix}::build wheel")


    version   = CmdTask("pip", "--version", verbosity=2, basename=f"{prefix}::version")
    upgrade   = CmdTask("pip", "install", "--upgrade", basename=f"{prefix}::upgrade")

    return [editlib, install, srcbuild, wheel, uninstall, version, upgrade]

def pip_requirements() -> dict:
    """:: generate requirements.txt """
    target = "requirements.txt"
    args1 = ["pip", "freeze", "--all", "--exclude-editable",
             "-r", "requirements.txt", ">", target]
    args2 = ["pip", "list", "--format=freeze", ">", target]

    return {
        'basename': f"{prefix}::requirements",
        "actions" : [ CmdAction(args1, shell=False),
                      CmdAction(args2, shell=False),
                     ],
        "targets" : [ target ],
        "clean"   : True,
    }
