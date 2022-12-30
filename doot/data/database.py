##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils import globber

##-- end imports


def build_sqlite_check(build):
        sqlite_dir_check = CheckDir(paths=[build],
                                    name="sqlite",
                                    task_dep=["_checkdir::build"])


class SqlitePrepTask(globber.FileGlobberMulti):
    """ file conversion from mysql to sqlite
    using https://github.com/dumblob/mysql2sqlite
    # TODO
    """
    def __init__(self, srcs):
        super().__init__("sqlite::prep", [".sql"], srcs, rec=True)

    def subtask_detail(self, fpath, task):
        return task

class SqliteReportTask(globber.FileGlobberMulti):
    """
    TODO report database tables
     .schema .fullschema
     .table
    """

    def __init__(self, srcs, build_dir):
        super().__init__("sqlite::report", [".db"], srcs, rec=True)
        self.build_dir = build_dir

    def subtask_detail(self, fpath, task):
        return task

    def subtask_actions(self, fapth):
        return []
