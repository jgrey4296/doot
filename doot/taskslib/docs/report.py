##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

import doot
from doot import globber

##-- end imports

class LineReport(globber.DirGlobMixin, globber.DootEagerGlobber):
    """
    Glob for all files in a target, and report on the amount of lines
    """

    def __init__(self, name="report::linecount", locs=None, roots=None, exts=None, rec=False):
        super().__init__(name, locs, roots or [locs.src], exts=exts, rec=rec)
        self.counts = {}

    def task_detail(self, task):
        task.update({
            "actions": [
                # sort counts
                # write to output report
            ],
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions": [
                # Glob For Files
                # line count them
                # add to counts
            ],
        })
        return task

def task_line_report(locs:DootLocData):
    """
    ([src] -> build) Generate a report of all files and their line count
    TODO update without pipes
    """
    return DeprecationWarning()
    find_cmd = ["find", locs.src, "-name", '"*.py"',
                "-not", "-name", '"test_*.py"',
                "-not", "-name", '"*__init__.py"',
                "-print0"]
    line_cmd = ["xargs", "-0", "wc", "-l"]
    sort_cmd = "sort"

    target = locs.build / "linecounts.report"

    return {
        "basename"  : "line-report",
        "actions"   : [ f"{find_cmd} | {line_cmd} | {sort_cmd} > {target}" ],
        "targets"   : [ target ],
        "task_dep"  : ["_checkdir::build"],
        "clean"     : True,
        "verbosity" : 2,
    }
