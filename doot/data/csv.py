#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from functools import partial
from doit.action import CmdAction
from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils import globber
from doot.utils import genx
##-- end imports

csv_dir = build_dir / "csv"

##-- check dir
csv_check = CheckDir(paths=[csv_dir], name="csv", task_dep=["_checkdir::build"])

##-- end check dir

class CSVSummaryTask(globber.FileGlobberMulti):
    """ Summarise all found csv files,
    grouping those with the same headers,
    and listing number of rows
    """

    def __init__(self):
        super(CSVSummaryTask, self).__init__("csv::summary",
                                             [".csv"], [pl.Path("data")],
                                             rec=True)

    def setup_detail(self, task):
        report_name = csv_dir / "csv.report"
        task['actions']  = ["echo CSV Start", f"echo '' > {report_name}"]
        task["task_dep"] = ["_checkdir::csv"]
        return task

    def teardown_detail(self, task):
        report_name = csv_dir / "csv.report"
        task['actions'] = [f"cat {report_name}", "echo Finished CSV"]
        return task

    def write_path(self, task):
        report_name = csv_dir / "csv.report"
        with open(report_name, 'a') as f:
            f.write(f"{task.meta['focus']}: ")

    def subtask_actions(self, fpath):
        report_name = csv_dir / "csv.report"
        return [
            self.write_path,
            f"cat {fpath} | wc -l | sed -e 's/$/ Columns: /' -e 's/^/Lines: /' | tr -d \"\n\" >> {report_name}",
            f"head --lines=1 {fpath} | sed -e 's/\r//g' >> {report_name}",
        ]

    def subtask_detail(self, fpath, task):
        task.update({
            "clean"    : True,
        })
        task['meta'].update({ "focus" : fpath })
        return task


class CSVSummaryXMLTask(globber.FileGlobberMulti):
    """ Summarise all found csv files,
    grouping those with the same headers,
    and listing number of rows
    """

    def __init__(self):
        super(CSVSummaryXMLTask, self).__init__("csv::summary.xml",
                                             [".csv"], [pl.Path("data")],
                                             rec=True)
        self.report_name = csv_dir / "csv.xml"

    def setup_detail(self, task):
        task['actions']  = [genx.create_xml(self.report_name)]
        task["task_dep"] = ["_checkdir::csv"]
        return task

    def teardown_detail(self, task):
        task['actions'] = [f"cat {self.report_name}", "echo Finished CSV"]
        return task


    def create_entry(self, fpath):
        cmds = [ genx.sub_xml("/data", "csv_file")  #
                 ,genx.attr_xml("/data/csv_file[count\(/data/csv_file\)]", "file", fpath)
                ]

        cmds_combined = " ".join(cmds)
        return CmdAction(f"xml ed -L {cmds_combined} {self.report_name}")

    def write_lines(self, fpath):
        cmd = genx.record_xml("/data/csv_file[count\(/data/csv_file\)]", "num_lines", "%s")
        total_cmd  = f"cat {fpath} | wc -l | xargs -I %s xml ed -L {cmd} {self.report_name}"

        return CmdAction(total_cmd)

    def head_line(self, fpath, task):
        cmd = genx.record_xml("/data/csv_file[count\(/data/csv_file\)]", "head", task.values['head'].strip())
        total_cmd      = f"xml ed -L {cmd} {self.report_name}"
        return total_cmd

    def subtask_actions(self, fpath):
        return [
            self.create_entry(fpath),
            self.write_lines(fpath),
            CmdAction(f"head --lines=1 {fpath} | sed -e 's/\r//g'", save_out="head"),
            CmdAction(partial(self.head_line, fpath)),
        ]

    def subtask_detail(self, fpath, task):
        task.update({
            "clean"    : True,
        })
        task['meta'].update({ "focus" : fpath })
        return task
