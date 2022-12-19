##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports


class SqlitePrepTask():
    """ file conversion from mysql to sqlite """
    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        pass

class SqliteReportTask:
    # report database tables
    # .schema .fullschema
    # .table

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        pass
