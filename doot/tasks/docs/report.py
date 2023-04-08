##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

import doot
from doot import globber

##-- end imports

from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin

class LineReport(DelayedMixin, TargetedMixin, globber.DootEagerGlobber):
    """
    Glob for all files in a target, and report on the amount of lines
    """

    def __init__(self, name="report::linecount", locs=None, roots=None, exts=None, rec=False):
        super().__init__(name, locs, roots or [locs.src], exts=exts, rec=rec)
        self.counts = []
        self.output = locs.build / "linecount.report"

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_file():
            return self.globc.accept
        return self.globc.discard

    def task_detail(self, task):
        task.update({
            "actions": [
                self.write_report,
            ],
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions": [
                (self.store_count, [fpath]),
            ],
        })
        return task

    def store_count(self, fpath):
        cmd = self.make_cmd("wc", "-l", fpath)
        cmd.execute()
        self.counts.append(cmd.result.strip())

    def write_report(self):
        report = [
            "Line Count Report:",
            "--------------------",
            "",
        ] + sorted(self.counts, key=lambda x: int(x.split(" ")[0]))


        self.output.write_text("\n".join(report))
