##-- imports
from __future__ import annotations
import pathlib as pl
import shutil
from doit.action import CmdAction
from doot.utils.tasker import DootTasker

##-- end imports

class CmdTask(DootTasker):

    def __init__(self, cmd, *args, data=None, **kwargs):
        super().__init__(kwargs['basename'], None)
        self.cmd    = cmd
        self.args   = list(args)
        self.kwargs = kwargs

    def task_detail(self, task) -> dict:
        task.update({
            "actions" : [ CmdAction([self.cmd] + self.args, shell=False) ],
        })
        task.update(self.kwargs)
        return task
