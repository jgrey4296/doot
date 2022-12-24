#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils.globber import EarlyGlobber

##-- end imports

csv_dir = build_dir / "csv"

##-- check dir
csv_check = CheckDir(paths=[csv_dir], name="csv", task_dep=["_checkdir::build"])

##-- end check dir

class CSVSummaryTask(EarlyGlobber):
    """ Summarise all found csv files,
    grouping those with the same headers,
    and listing number of rows
    """

    def __init__(self):
        super(CSVSummaryTask, self).__init__("csv::summary",
                                             [".csv"],
                                             [pl.Path("data")])

    def get_actions(self, fname):
        return [f"head --lines=1 {fname}"]
