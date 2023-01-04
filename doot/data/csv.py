#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from functools import partial

from doit.action import CmdAction

import doot
from doot.files.checkdir import CheckDir
from doot.utils import genx, globber
from doot.utils.cmdtask import CmdTask
##-- end imports


class CSVSummaryTask(globber.FileGlobberMulti):
    """ Summarise all found csv files,
    grouping those with the same headers,
    and listing number of rows
    """

k   def __init__(self, dirs:DootLocData, roots):
        super().__init__("csv::summary", dirs, roots, exts=[".csv"], rec=True)
        report_name = self.dirs.build / "csv.report"

    def setup_detail(self, task):
        task['actions']  = [lambda: report_name.unlink(missing_ok=True) ],
        return task

    def teardown_detail(self, task):
        task['actions'] = [CmdAction(["cat", self.report_name], shell=False) ],
        return task

    def subtask_detail(self, fpath, task):
        task.update({
            "clean"    : True,
        })
        return task


    def subtask_actions(self, fpath):
        return [
            partial(self.write_path, fpath),
            # CmdAction(f"cat {fpath} | wc -l | sed -e 's/$/ Columns: /' -e 's/^/Lines: /' | tr -d \"\n\" >> {report_name}"),
            # CmdAction(f"head --lines=1 {fpath} | sed -e 's/\r//g' >> {report_name}"),
        ]

    def write_data(self, fpath, task):
        text        = fpath.read_text().split("\n")
        columns     = len(text[0].split(","))
        with open(self.report_name, 'a') as f:
            f.write(str(fpath), ": ")
            f.write("Rows: ", len(text), " ")
            f.write("Columns: ", columns, " ")
            f.write("Header: ", text[0].strip(), "\n")



class CSVSummaryXMLTask(globber.FileGlobberMulti):
    """ Summarise all found csv files,
    grouping those with the same headers,
    and listing number of rows
    """

    def __init__(self, dirs:DootLocData, roots):
        super().__init__("csv::summary.xml", dirs, roots, exts=[".csv"], rec=True)
        self.report_name = self.dirs.build / "csv.xml"

    def setup_detail(self, task):
        task['actions']  = [lambda: genx.create_xml(self.report_name)]
        return task

    def teardown_detail(self, task):
        task['actions'] = [f"cat {self.report_name}"]
        return task

    def subtask_detail(self, fpath, task):
        task.update({"clean" : True,})
        return task

    def subtask_actions(self, fpath):
        return [
            self.create_entry(fpath),
            CmdAction(partial(self.write_lines, fpath), shell=False),
            CmdAction(partial(self.head_line, fpath)),
        ]

    def create_entry(self, fpath):
        cmds = ["xml", "ed", "-L" ]
        cmds += genx.sub_xml("/data", "csv_file")
        cmds += genx.attr_xml("/data/csv_file[count\(/data/csv_file\)]", "file", fpath)
        cmds.append(self.report_name)

        return CmdAction(cmds, shell=False)

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
