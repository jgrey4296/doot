##-- imports
from __future__ import annotations
import pathlib as pl
import shutil

from doit import create_after
from doit.action import CmdAction
from doit.tools import (Interactive, PythonInteractiveAction, create_folder,
                        set_trace)

try:
    # For py 3.11 onwards:
    import tomllib as toml
except ImportError:
    # Fallback to external package
    import toml
##-- end imports

def load_toml(path="pyproject.tol"):
    return toml.load(path)

def make_task(func):
    """ decorate a function to be a task-creator """
    func.create_doit_tasks = func
    return func

def build_cmd(cmd, args):
    return " ".join([cmd] + [str(x) for x in args])

def force_clean_targets(task, dryrun):
    """ remove all targets from a task
    Add to a tasks 'clean' dict value
    """
    for target_s in sorted(task.targets, reverse=True):
        try:
            target = pl.Path(target_s)
            if dryrun:
                print("%s - dryrun removing '%s'" % (task.name, target))
                continue

            print("%s - removing '%s'" % (task.name, target))
            if target.is_file():
                target.remove()
            elif target.is_dir():
                shutil.rmtree(str(target))
        except OSError as err:
            print(err)

class JGCmdTask:

    def __init__(self, cmd, *args, data=None, **kwargs):
        self.create_doit_tasks = self.make
        self.cmd               = cmd
        self.args              = args
        self.kwargs            = kwargs

    def make(self) -> dict:
        task_desc = self.kwargs.copy()
        task_desc['actions'] = [ build_cmd(self.cmd, self.args) ]
        return task_desc
