##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from doit.action import CmdAction

import doot
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.tasker import DootTasker

##-- end imports

class GitLogTask(DootTasker):
    """
    ([root] -> build) Output a summary of the git repo, with a specific format
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
    TODO (build -> build) separate the printed log
    """

    def __init__(self, dirs):
        super().__init__("git::analysis", dirs)
        self.times  = {}
        self.days   = {}
        self.months = {}
        # streaks / breaks
        # weekends / weekdays
        # day / night
        # tags
        # files touched

    def task_detail(self, task):
        task.update({
            "targets"  : [ self.dirs.build / "time.distribution",
                           self.dirs.build / "day.distribution",
                           self.dirs.build / "month.distribution",
                           ],
            "file_dep" : [ self.dirs.build / "full_git.log" ],
            "actions"  : [ self.process_log,
                           self.write_distributions,
                           ],
        })
        return task

    def process_log(self, targets):
        for line in (self.dirs.build / "full_git.log").read_text().split("\n"):
            #
            pass

    def write_distributions(self):
        pass
