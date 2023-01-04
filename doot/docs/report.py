##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils import globber

##-- end imports


def task_line_report(dirs:DootDirs):
    """
    Generate a report of all files and their line count
    TODO update without pipes
    """
    find_cmd = ["find", dirs.src, "-name", '"*.py"',
                "-not", "-name", '"test_*.py"',
                "-not", "-name", '"*__init__.py"',
                "-print0"])
    line_cmd = ["xargs", "-0", "wc", "-l"])
    sort_cmd = "sort"

    target = dirs.build / "linecounts.report"

    return {
        "basename"  : "line-report",
        "actions"   : [ f"{find_cmd} | {line_cmd} | {sort_cmd} > {target}" ],
        "targets"   : [ target ],
        "task_dep"  : ["_checkdir::build"],
        "clean"     : True,
        "verbosity" : 2,
    }
