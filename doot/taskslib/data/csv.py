#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from functools import partial

import doot
from doot.taskslib.utils import genx
from doot import globber, tasker, task_mixins
##-- end imports

class CSVSummaryTask(globber.DootEagerGlobber, task_mixins.ActionsMixin):
    """
    ([data] -> build) Summarise all found csv files,
    grouping those with the same headers,
    and listing number of rows
    """

    def __init__(self, name="csv::summary", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".csv"], rec=rec)
        self.report_name = self.locs.build / "csv.report"

    def setup_detail(self, task):
        task['actions']  = [ (self.rmfiles, [self.report_name]) ]
        return task

    def task_detail(self, task):
        task['teardown'] = [self.cmd(["cat", self.report_name]) ]
        return task

    def subtask_detail(self, task, fpath=None):
        task.update({
            "clean"    : True,
            "actions" : [
                (self.write_data, [fpath]),
                # CmdAction(f"cat {fpath} | wc -l | sed -e 's/$/ Columns: /' -e 's/^/Lines: /' | tr -d \"\n\" >> {report_name}"),
                # CmdAction(f"head --lines=1 {fpath} | sed -e 's/\r//g' >> {report_name}"),
            ]
            })
        return task

    def write_data(self, fpath, task):
        text        = fpath.read_text().split("\n")
        columns     = len(text[0].split(","))
        with open(self.report_name, 'a') as f:
            f.write(str(fpath), ": ")
            f.write("Rows: ", len(text), " ")
            f.write("Columns: ", columns, " ")
            f.write("Header: ", text[0].strip(), "\n")

class CSVSummaryXMLTask(globber.DootEagerGlobber, task_mixins.ActionsMixin):
    """
    ([data] -> build) Summarise all found csv files, using xmlstarlet
    grouping those with the same headers,
    and listing number of rows
    """

    def __init__(self, name="csv::summary.xml", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".csv"], rec=rec)
        self.report_name = self.locs.build / "csv.xml"

    def setup_detail(self, task):
        task['actions']  = [lambda: genx.create_xml(self.report_name)]
        return task

    def task_detail(self, task):
        task['teardown'] = [f"cat {self.report_name}"]
        return task

    def subtask_detail(self, task, fpath=None):
        task.update({"clean" : True,
                     "actions" : [
                         self.cmd(self.create_entry, fpath),
                         self.cmd(self.write_lines, fpath),
                         self.cmd(self.head_line, fpath),
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
