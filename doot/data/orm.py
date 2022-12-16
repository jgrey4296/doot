##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports

# TODO target into build_dir
def task_xml_python_orm():
    cmd = "xsdata"
    args = ["generate",
            "-r", # recursive
            "-p", "{targets}", # generate package name
            "--relative-imports", "--postponed-annotations",
            "--kw-only",
            "--frozen",
            "--no-unnest-classes",
            "{file_dep}"]
    return {
        "actions"  : [build_cmd(cmd, args)],
        "targets"  : ["out_package"],
        "file_dep" : ["schema.xsd"], # xml, json, xsd
    }
