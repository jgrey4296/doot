##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from doit.action import CmdAction

import doot
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.task_group import TaskGroup
from doot.files.clean_dirs import clean_target_dirs
from doot.utils.tasker import DootTasker

##-- end imports

__all__ = [
        "SphinxDocTask", "task_browse",
]


conf_builder    = doot.config.or_get("html").tool.doot.sphinx.builder()
conf_verbosity  = int(doot.config.or_get("0").tool.door.sphinx.verbosity())

class SphinxDocTask(DootTasker):
    """([docs] -> build) Build sphinx documentation """

    def __init__(self, dirs:DootLocData, builder=None, verbosity:int=None):
        super().__init__("sphinx::doc", dirs)
        self.builder = builder or conf_builder
        self.verbosity = verbosity or conf_verbosity

    def task_detail(self, task:dict) -> dict:
        return {
            "actions"  : [ CmdAction(self.sphinx_command, shell=False) ],
            "file_dep" : [ self.dirs.docs / "conf.py" ],
            "targets"  : [ self.dirs.build / "index.html" ],
            "clean"    : [ clean_target_dirs ],
        }


    def sphinx_command(self):
        args = ["sphinx-build", '-b', self.builder, self.dirs.docs, self.dirs.build]
        match self.verbosity:
            case x if x > 0:
                args += ["-v" for i in range(x)]
            case x if x == -1:
                args.append("-q")
            case x if x == -2:
                args.append("-Q")

        return args


    def gen_toml(self):
        return """
##-- sphinx
[tool.doot.sphinx]
builder   = "html"
verbosity = 0
##-- end sphinx
"""

def task_browse(dirs:DootLocData) -> dict:
    """[build] Task definition """
    assert("html" in dirs.extra)
    return {
        "basename"    : "sphinx::browse",
        "actions"     : [ CmdAction([ "open",  dirs.extra['html'] ], shell=False) ],
        "task_dep"    : ["sphinx::build"],
    }

