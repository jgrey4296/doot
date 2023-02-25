##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from typing import Final

import doot
from doot.task_group import TaskGroup
from doot.tasker import DootTasker

##-- end imports

__all__ = [
        "SphinxDocTask", "task_browse",
]

from doot.mixins.commander import CommanderMixin
from doot.mixins.cleaning import CleanerMixin

conf_builder     : Final = doot.config.on_fail("html", str).tool.doot.sphinx.builder()
conf_verbosity   : Final = doot.config.on_fail(0, int).tool.door.sphinx.verbosity()

def task_browse() -> dict:
    """[build] Task definition """
    doot.locs.ensure("html")
    return {
        "basename"    : "sphinx::browse",
        "actions"     : [ CommanderMixin.cmd(None, ["open", doot.locs.html ]) ],
        "task_dep"    : ["sphinx::doc"],
    }

class SphinxDocTask(DootTasker, CleanerMixin, CommanderMixin):
    """([docs] -> build) Build sphinx documentation """

    def __init__(self, name="sphinx::doc", locs:DootLocData=None, builder=None, verbosity:int=None):
        super().__init__(name, locs)
        self.builder = builder or conf_builder
        self.verbosity = verbosity or conf_verbosity
        self.locs.ensure("docs", "html", "build")

    def task_detail(self, task:dict) -> dict:
        task.update({
            "actions"  : [ self.cmd(self.sphinx_command) ],
            "file_dep" : [ self.locs.docs / "conf.py" ],
            "targets"  : [ self.locs.html, self.locs.build ],
            "clean"    : [ self.clean_target_dirs ],
        })
        return task

    def sphinx_command(self):
        args = ["sphinx-build",
                '-b', self.builder,
                self.locs.docs,
                self.locs.build]
        match self.verbosity:
            case x if x > 0:
                args += ["-v" for i in range(x)]
            case x if x == -1:
                args.append("-q")
            case x if x == -2:
                args.append("-Q")

        return args
