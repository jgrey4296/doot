##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from doot import globber
from doot import tasker

##-- end imports

class SqlitePrepTask(globber.DootEagerGlobber, tasker.ActionsMixin):
    """
    ([data] -> data) file conversion from mysql to sqlite
    using https://github.com/dumblob/mysql2sqlite
    # TODO
    """
    def __init__(self, name="sqlite::prep", dirs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".sql"], rec=rec)

    def subtask_detail(self, task, fpath=None):
        return task

class SqliteReportTask(globber.DootEagerGlobber, tasker.ActionsMixin):
    """
    TODO ([data] -> build) report database tables
     .schema .fullschema
     .table
    """

    def __init__(self, name="sqlite::report", dirs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".db"], rec=rec)

    def subtask_detail(self, task, fpath=None):
        task['actions'] += self.subtask_actions(fpath)
        return task

    def subtask_actions(self, fapth):
        return []
