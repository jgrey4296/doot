##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils import globber

##-- end imports

sqlite_build_dir = build_dir / "sqlite"

##-- dir checks
sqlite_dir_check = CheckDir(paths=[sqlite_build_dir,], name="sqlite", task_dep=["_checkdir::build"])

##-- end dir checks

class SqlitePrepTask(globber.FileGlobberMulti):
    """ file conversion from mysql to sqlite
    using https://github.com/dumblob/mysql2sqlite
    """
    def __init__(self):
        super().__init__("sqlite::prep", [".sql"], [src_dir], rec=True)

    def subtask_detail(self, fpath, task):
        return task

class SqliteReportTask(globber.FileGlobberMulti):
    # report database tables
    # .schema .fullschema
    # .table

    def __init__(self):
        super().__init__("sqlite::report", [".db"], [src_dir], rec=True)

    def subtask_detail(self, fpath, task):
        return task
