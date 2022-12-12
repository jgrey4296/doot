##-- imports
from __future__ import annotations

import pathlib as pl
import zipfile

from doot import build_dir, datatoml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports

class ZipFiles:
    """
    Automate creation of archive zipfiles
    # TODO auto-name by time and date
    """
    def __init__(self, target, *paths, globs=None, data=None, **kwargs):
        assert(target.suffix == ".zip")
        self.create_doit_tasks = self.build
        self.target            = target
        self.args              = [pl.Path(x) for x in paths]
        self.globs             = globs or []
        self.kwargs            = kwargs

    def action_zip_create(self
        with open(self.target, 'w') as targ:
            for dep in file_dep:
                targ.write(dep)

    def action_zip_glob(self):
        with open(self.target, 'w') as targ:
            for glob in globs:
                for dep in glob:
                    targ.write(dep)

    # def uptodate(self):
    #     return all([x.exists() for x in self.args])

    def build(self) -> dict:
        task_desc = self.kwargs.copy()
        task_desc.update({
            "actions"  : [ self.action_zip_create],
            "targets"  : [ self.target ],
            "uptodate" : [ self.uptodate ],
            "clean"    : True,
            "task_dep" : ["checkdir::build"],
        })
        return task_desc



