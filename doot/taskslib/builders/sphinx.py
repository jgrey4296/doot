##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

import doot
from doot.task_group import TaskGroup
from doot.utils.clean_actions import clean_target_dirs
from doot.tasker import DootTasker, DootActions

##-- end imports

__all__ = [
        "SphinxDocTask", "task_browse",
]

conf_builder    = doot.config.or_get("html", str).tool.doot.sphinx.builder()
conf_verbosity  = int(doot.config.or_get(0, int).tool.door.sphinx.verbosity())

def gen_toml(self):
    return "\n".join(["[tool.doot.sphinx]",
                      "builder   = \"html\"",
                      "verbosity = 0",
                      ])

def task_browse(dirs:DootLocData) -> dict:
    """[build] Task definition """
    assert("html" in dirs.extra)
    return {
        "basename"    : "sphinx::browse",
        "actions"     : [ DootActions.cmd(None, ["open", dirs.extra['html'] ]) ],
        "task_dep"    : ["sphinx::doc"],
    }

class SphinxDocTask(DootTasker, DootActions):
    """([docs] -> build) Build sphinx documentation """
    gen_toml = gen_toml

    def __init__(self, name="sphinx::doc", dirs:DootLocData=None, builder=None, verbosity:int=None):
        super().__init__(name, dirs)
        self.builder = builder or conf_builder
        self.verbosity = verbosity or conf_verbosity

    def task_detail(self, task:dict) -> dict:
        task.update({
            "actions"  : [ self.cmd(self.sphinx_command) ],
            "file_dep" : [ self.dirs.docs / "conf.py" ],
            "targets"  : [ self.dirs.extra['html'], self.dirs.build ],
            "clean"    : [ clean_target_dirs ],
        })
        return task

    def sphinx_command(self):
        args = ["sphinx-build",
                '-b', self.builder,
                self.dirs.docs,
                self.dirs.build]
        match self.verbosity:
            case x if x > 0:
                args += ["-v" for i in range(x)]
            case x if x == -1:
                args.append("-q")
            case x if x == -2:
                args.append("-Q")

        return args
