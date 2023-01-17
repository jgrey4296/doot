##-- imports
from __future__ import annotations
import pathlib as pl
import shutil
from doit.action import CmdAction
from doot.tasker import DootTasker

##-- end imports

class CmdTask(DootTasker):

    def __init__(self, name="default:cmdtask", dirs=None, *args, **kwargs):
        super().__init__(name, dirs)
        self.args   = list(args)
        self.kwargs = kwargs

    def task_detail(self, task) -> dict:
        task.update({
            "actions" : [ CmdAction(self.args, shell=False) ],
        })
        task.update(self.kwargs)
        return task
