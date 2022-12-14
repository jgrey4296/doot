##-- imports
from __future__ import annotations
from doit.action import CmdAction

##-- end imports

def make_task(func):
    """ decorate a function to be a task-creator """
    func.create_doit_tasks = func
    return func

def build_cmd(cmd, args, **kwargs):
    return CmdAction(" ".join([cmd] + [str(x) for x in args]), **kwargs)
