##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from doit.action import CmdAction

import doot
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.tasker import DootTasker

##-- end imports

class GitLogTask(DootTasker):
    """
    Output a summary of the git repo, with a specific format
    see: https://git-scm.com/docs/git-log
    """

    def __init__(self, dirs:DootLocData, fmt="%ai :: %h :: %al :: %s"):
        super().__init__("git::logs", dirs)
        self.format = fmt

    def task_detail(self, task):
        task.update({
            "actions"  : [ CmdAction(self.get_log, shell=False, save_out="result"),
                           self.save_log,
                          ],
            "targets"  : [ self.dirs.build / "full_git.log" ],
            "clean"    : True,
        })
        return task


    def get_log(self):
        return ["git", "log", f"--pretty=format:{self.format}"]

    def save_log(self, task, targets):
        result = task.values['result']
        pl.Path(targets[0]).write_text(result)
        print("\n")

class GitLogAnalyseTask(DootTasker):
    """
    TODO separate the printed log
    """

    def __init__(self, dirs):
        super().__init__("git::analysis", dirs)

    def task_detail(self, task):
        task.update({
            "targets"  : [ self.dirs.build / "time.distribution",
                           self.dirs.build / "day.distribution",
                           self.dirs.build / "month.distribution",
                           ],
            "file_dep" : [ self.dirs.build / "full_git.log" ],
            "actions"  : [ self.get_time_dist,
                           self.get_day_dist,
                           self.get_month_dist ],
        })
        return task

    def get_time_dist(self, task):
        # read log
        # group into bins
        # print out
        pass

    def get_day_dist(self, task):
        pass


    def get_month_dist(self, task):
        pass
