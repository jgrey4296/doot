##-- imports
from __future__ import annotations

from typing import Final
import pathlib as pl
import shutil

import doot
from doot import tasker, globber, task_mixins

##-- end imports

from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin

listing_roots = doot.config.on_fail([], list).tool.doot.listing.core()
glob_ignores : Final = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).tool.doot.globbing.ignores()

class FileListings(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin):
    """
    (-> build )list all files in the targ directory,
    to the build_dir/allfiles.report
    """

    def __init__(self, name="listing::files", locs=None, roots=None, rec=False, exts=None):
        list_these = [getattr(locs, x) for x in listing_roots]
        super().__init__(name, locs, roots or list_these , rec=rec, exts=exts)
        self.output = self.locs.on_fail(self.locs.build).listings_out()

    def filter(self, fpath):
        if fpath.is_dir():
            return self.control.keep
        self.control.discard

    def subtask_detail(self, task, fpath):
        report = self.output / f"{task['name']}.listing"
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

class SimpleListing(tasker.DootTasker, task_mixins.ActionsMixin):
    """
    (-> build ) ripgrep list all files in the focus, or root
    to the build_dir/allfiles.report
    """

    def __init__(self, name="listing::simple", locs=None, focus=None):
        super().__init__(name, locs)
        self.focus = focus or locs.root
        self.locs.ensure("build")

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
