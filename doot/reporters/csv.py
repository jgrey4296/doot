#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from functools import partial

import doot
from doot.tasks.utils import genx
from doot import globber, tasker
##-- end imports

from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.csv import CSVMixin

class CSVSummaryTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, FilerMixn, CSVMixin):
    """
    ([data] -> build) Summarise all found csv files,
    grouping those with the same headers,
    and listing number of rows
    # TODO actually load the csv
    """

    def __init__(self, name="report::csv", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".csv"], rec=rec)
        self.output = self.locs.build / "csv.report"

    def set_params(self):
        return self.target_params()

    def setup_detail(self, task):
        task['actions']  = [ (self.rmfiles, [self.report_name]) ]
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "clean"    : True,
            "actions" : [
                (self.csv_summary, [fpath]), # -> report/rows/columsn/header
                (self.append_to, [self.output, "report"]),
            ]
        })
        return task

class CSVSummaryXMLTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin):
    """
    ([data] -> build) Summarise all found csv files, using xmlstarlet
    grouping those with the same headers,
    and listing number of rows
    """

    def __init__(self, name="report::csv.xml", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".csv"], rec=rec)
        self.report_name = self.locs.build / "csv.xml"


    def set_params(self):
        return self.target_params()

    def setup_detail(self, task):
        task['actions']  = [lambda: genx.create_xml(self.report_name)]
        return task

    def task_detail(self, task):
        task['teardown'] = [f"cat {self.report_name}"]
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [
                self.make_cmd(self.create_entry, fpath),
                self.make_cmd(self.write_lines, fpath),
                self.make_cmd(self.head_line, fpath),
            ],
        })
        return task

    def create_entry(self, fpath):
        cmds = ["xml", "ed", "-L" ]
        cmds += genx.sub_xml("/data", "csv_file")
        cmds += genx.attr_xml("/data/csv_file[count\(/data/csv_file\)]", "file", fpath)
        cmds.append(self.report_name)

        return cmds

    def write_lines(self, fpath):
        line_count = len(fpath.read_text().split("\n"))
        cmds = ["xml", "ed", "-L"]
        cmds += genx.record_xml("/data/csv_file[count\(/data/csv_file\)]", "num_lines", line_count)
        cmds.append(self.report_name)
        # total_cmd  = f"cat {fpath} | wc -l | xargs -I %s xml ed -L {cmd} {self.report_name}"
        return cmds

    def head_line(self, fpath, task):
        head = fpath.read_text().split("\n")[0].strip()
        cmds = ["xml", "ed", "-L"]
        cmds += genx.record_xml("/data/csv_file[count\(/data/csv_file\)]", "head", head)
        cmds.append(self.report_name)
        # total_cmd      = f"xml ed -L {cmd} {self.report_name}"
        return cmds
