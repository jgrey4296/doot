##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports


def task_line_report():
    find_cmd = build_cmd("find",
                         [src_dir, "-name", '"*.py"',
                          "-not", "-name", '"test_*.py"',
                          "-not", "-name", '"*__init__.py"',
                          "-print0"])
    line_cmd = build_cmd("xargs", ["-0", "wc", "-l"])
    sort_cmd = build_cmd("sort", [])

    target = build_dir / "linecounts.report"

    return {
        "basename"  : "line-report",
        "actions"   : [ f"{find_cmd} | {line_cmd} | {sort_cmd} > {target}" ],
        "targets"   : [ target ],
        "task_dep"  : ["_checkdir::build"],
        "clean"     : True,
        "verbosity" : 2,
    }
