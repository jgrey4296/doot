##-- imports
from __future__ import annotations
import pathlib as pl
import shutil

from doot.files.clean_dirs import clean_target_dirs
##-- end imports

class CheckDir:
    """ Task for checking directories exist,
    making them if they don't
    """

    def __init__(self, *, paths=None, data=None, name="default", **kwargs):
        self.create_doit_tasks = self.build
        self.paths             = [pl.Path(x) for x in paths or [] ]
        self.kwargs            = kwargs
        self.default_spec      = { "basename" : f"_checkdir::{name}" }

    def uptodate(self):
        return all([x.exists() for x in self.args])

    def mkdir(self):
        for x in self.paths:
            try:
                x.mkdir(parents=True)
            except FileExistsError:
                print(f"{x} already exists")
                pass

    def build(self) -> dict:
        task_desc = self.default_spec.copy()
        task_desc.update(self.kwargs)
        task_desc.update({
            "actions"  : [ self.mkdir ],
            "targets"  : self.paths,
            "uptodate" : [ self.uptodate ],
            "clean"    : [ clean_target_dirs ],
        })
        return task_desc

class DestroyDir:
    """ Task that destroys a directory. ie: working directories """

    def __init__(self, *, paths=None, data=None, name="default", **kwargs):
        self.create_doit_tasks = self.build
        self.paths             = [pl.Path(x) for x in paths or [] ]
        self.kwargs            = kwargs
        self.default_spec      = { "basename" : f"destroydir::{name}" }

    def uptodate(self):
        return all([x.exists() for x in self.args])

    def destroy_deps(task, dryrun):
        """ Clean targets, including non-empty directories
        Add to a tasks 'clean' dict value
        """
        for target_s in sorted(task.file_dep, reverse=True):
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

    def build(self):
        task_desc = self.default_spec.copy()
        task_desc.update(self.kwargs)
        task_desc.update({
            "actions"  : [ self.destroy_deps ],
            "file_dep" : self.paths,
            "uptodate" : [ self.uptodate ],
        })
        return task_desc
