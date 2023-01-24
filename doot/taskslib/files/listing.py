##-- imports
from __future__ import annotations

from typing import Final
import pathlib as pl
import shutil

import doot
from doot import tasker, globber

##-- end imports

glob_ignores : Final = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).tool.doot.globbing.ignores()

class FileListings(globber.DirGlobMixin, globber.DootEagerGlobber, tasker.ActionsMixin):
    """
    (-> build )list all files in the targ directory,
    to the build_dir/allfiles.report
    """

    def __init__(self, name="listing::files", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [x[1] for x in locs], rec=rec, exts=exts)

    def subtask_detail(self, task, fpath):
        report = self.locs.build / f"{task['name']}.listing"
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

    def __init__(self, name="listing::simple", locs=None, focus=None):
        super().__init__(name, locs)
        self.focus = focus or locs.root

    def task_detail(self, task):
        report = self.locs.build / f"{task['name']}.listing"
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


class EncodingListing(globber.DirGlobMixin, globber.DootEagerGlobber):
    """
    file -I {}
    iconv -f {enc} -t {enc} {} > conv-{}
    """
    pass
