##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils import globber

##-- end imports

class SqlitePrepTask(globber.FileGlobberMulti):
    """ file conversion from mysql to sqlite
    using https://github.com/dumblob/mysql2sqlite
    # TODO
    """
    def __init__(self, dirs:DootDirs):
        super().__init__("sqlite::prep", dirs, [dirs.data], exts=[".sql"], rec=True)

    def subtask_detail(self, fpath, task):
        return task

class SqliteReportTask(globber.FileGlobberMulti):
    """
    TODO report database tables
     .schema .fullschema
     .table
    """

    def __init__(self, dirs:DootDirs):
        super().__init__("sqlite::report", dirs, [dirs.data], [".db"], rec=True)

    def subtask_detail(self, fpath, task):
        return task

    def subtask_actions(self, fapth):
        return []
