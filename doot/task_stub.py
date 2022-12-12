##-- imports
from __future__ import annotations
import pathlib as pl
##-- end imports

class TaskStub:
    """
    A Stub for easily building tasks
    """

    def __init__(self, *args, **kwargs):
        self.create_doit_tasks = self.build

    def uptodate(self):
        return True

    def action(self):
        pass

    def build(self) -> dict:
        return {
            "actions": [self.action],
            "targets" : [],
        }

    def gen_toml(self):
        """ generate a toml skeleton for customizing this task? """
        pass
