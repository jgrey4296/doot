##-- imports
from __future__ import annotations
import pathlib as pl
import shutil

from doot.files.force_clean import force_clean_targets
##-- end imports

class CheckDir:
    """ Task for checking directories exist,
    making them if they don't
    """

    def __init__(self, *paths, data=None, **kwargs):
        self.create_doit_tasks = self.build
        self.args              = [pl.Path(x) for x in paths]
        self.kwargs            = kwargs

    def uptodate(self):
        return all([x.exists() for x in self.args])

    def mkdir(self):
        for x in self.args:
            try:
                x.mkdir(parents=True)
            except FileExistsError:
                print(f"{x} already exists")
                pass

    def build(self) -> dict:
        task_desc = self.kwargs.copy()
        task_desc.update({
            "actions"  : [ self.mkdir ],
            "targets"  : self.args,
            "uptodate" : [ self.uptodate ],
            "clean"    : [ force_clean_targets],
        })
        return task_desc

