##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

import doot
from doot import tasker, globber

##-- end imports

glob_ignores = doot.config.or_get(['.git', '.DS_Store', "__pycache__"], list).tool.doot.glob_ignores()

class FileListings(globber.DirGlobMixin, globber.DootEagerGlobber, tasker.ActionsMixin):
    """
    (-> build )list all files in the targ directory,
    to the build_dir/allfiles.report
    """

    def __init__(self, name="listing::files", dirs=None, roots=None, rec=False, exts=None):
        super().__init__(name, dirs, roots or [dirs.src, dirs.data], rec=rec, exts=exts)

    def subtask_detail(self, task, fpath):
        report = self.dirs.build / f"{task['name']}.listing"
        task.update({
            "actions"  : [
                self.cmd(["rg", "--no-ignore", "--files", fpath], save="listing"),
                (self.write_to, [report, "listing"]),
            ],
            "targets"  : [ report ],
            "clean"    : True,
            "verbosity": 1,
        })
        return task

class SimpleListing(tasker.DootTasker, tasker.ActionsMixin):
    """
    (-> build ) ripgrep list all files in the focus, or root
    to the build_dir/allfiles.report
    """

    def __init__(self, name="listing::simple", dirs=None, focus=None):
        super().__init__(name, dirs)
        self.focus = focus or dirs.root

    def task_detail(self, task):
        report = self.dirs.build / f"{task['name']}.listing"
        task.update({
            "actions"  : [
                self.cmd(["rg", "--no-ignore", "--sort", "path", "--files", self.focus], save="listing"),
                (self.write_to, [report, "listing"]),
            ],
            "targets"  : [ report ],
            "clean"    : True,
            "verbosity": 1,
        })
        return task
