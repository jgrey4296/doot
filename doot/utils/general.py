##-- imports
from __future__ import annotations

##-- end imports

def make_task(func):
    """ decorate a function to be a task-creator """
    func.create_doit_tasks = func
    return func

def build_cmd(cmd, args):
    return " ".join([cmd] + [str(x) for x in args])

