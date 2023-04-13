##-- imports
from __future__ import annotations

from typing import Final
import pathlib as pl
import shutil

##-- end imports

import doot
from doot import tasker, globber
from doot.mixins.filer import FilerMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin

listing_roots = doot.config.on_fail(["root"], list).listing.core()
glob_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).globbing.ignores()

class FileListings(DelayedMixin, globber.DootEagerGlobber, FilerMixin, CommanderMixin):
    """
    (-> build )list all files in the targ directory,
    to the build_dir/allfiles.report
    """

    def __init__(self, name="report::files", locs=None, roots=None, rec=False, exts=None):
        list_these = [getattr(locs, x) for x in listing_roots]
        super().__init__(name, locs, roots or list_these , rec=rec, exts=exts)
        self.output = self.locs.temp

    def filter(self, fpath):
        if fpath.is_dir():
            return self.control.keep
        self.control.discard

    def subtask_detail(self, task, fpath):
        report = self.output / f"{task['name']}.listing"
        task.update({
            "actions"  : [
                self.make_cmd(["rg", "--no-ignore", "--files", fpath], save="listing"),
                (self.write_to, [report, "listing"]),
            ],
            "targets"  : [ report ],
            "clean"    : True,
            "verbosity": 1,
        })
        return task

class SimpleListing(tasker.DootTasker, CommanderMixin, FilerMixin):
    """
    (-> build ) ripgrep list all files in the focus, or root
    to the build_dir/allfiles.report
    """

    def __init__(self, name="listing::simple", locs=None, focus=None):
        super().__init__(name, locs)
        self.focus = focus or locs.root
        self.locs.ensure("build", task=name)

    def task_detail(self, task):
        report = self.locs.build / f"{task['name']}.listing"
        task.update({
            "actions"  : [
                self.make_cmd(["rg", "--no-ignore", "--sort", "path", "--files", self.focus], save="listing"),
                (self.write_to, [report, "listing"]),
            ],
            "targets"  : [ report ],
            "clean"    : True,
            "verbosity": 1,
        })
        return task
