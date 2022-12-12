##-- imports
from __future__ import annotations
import pathlib as pl
import shutil

##-- end imports

class CmdTask:
    """ Task for simple one-liners """

    def __init__(self, cmd, *args, data=None, **kwargs):
        self.create_doit_tasks = self.build
        self.cmd               = cmd
        self.args              = args
        self.kwargs            = kwargs

    def build(self) -> dict:
        task_desc = self.kwargs.copy()
        task_desc['actions'] = [ build_cmd(self.cmd, self.args) ]
        return task_desc
