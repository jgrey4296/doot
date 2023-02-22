##-- imports
"""
| .show              | List settings                                |                                                  |
| .mode              | Set output formatting mode                   | csv, column, html, insert, line, list, tabs, tcl |
| .nullvalue $STRING | set a default string in place of null values |                                                  |
| .schema $TABLE     | show the setup of a table                    |                                                  |
| .tables            | list all tables in the file                  |                                                  |
| .dump $TABLE       | output the table in SQL format               |                                                  |
| .headers on/off    | display headers on output                    |                                                  |
| .backup main $FILE | backup db main to a file                     |                                                  |
"""
from __future__ import annotations

import pathlib as pl
import shutil

from doot import globber, tasker, task_mixins

##-- end imports

class TODOSqlitePrepTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin):
    """
    ([data] -> data) file conversion from mysql to sqlite
    using https://github.com/dumblob/mysql2sqlite
    """

    def __init__(self, name="sqlite::prep", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".sql"], rec=rec)

    def set_params(self):
        return self.target_params()

    def subtask_detail(self, task, fpath=None):
        return task

class TODOSqliteReportTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin):
    """
    ([data] -> build) report database tables
     .schema .fullschema
     .table
    """

    def __init__(self, name="sqlite::report", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".db"], rec=rec)

    def set_params(self):
        return self.target_params()

    def subtask_detail(self, task, fpath=None):
        task['actions'] += self.subtask_actions(fpath)
        return task

    def subtask_actions(self, fapth):
        return []
