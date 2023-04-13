#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from functools import partial
import shlex

from functools import partial
from itertools import cycle, chain

import doot
from doot import globber, tasker

##-- end imports

from doot.mixins.commander import CommanderMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin

class JsonFormatTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, FilerMixin, CommanderMixin):
    """
    ([data] -> data) Lint Json files with jq *inplace*
    """

    def __init__(self, name="json::format.inplace", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".json"], rec=rec)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.globc.accept
        return self.globc.discard

    def subtask_detail(self, task, fpath=None):
        task.update({
            "uptodate" : [False],
            "actions" : [ (self.format_jsons_in_dir, [fpath]) ],
            })
        return task

    def sub_filter(self, fpath):
        if fpath.is_file() and fpath.suffix in self.exts:
            return self.globc.accept
        return self.globc.discard

    def format_jsons_in_dir(self, fpath):
        globbed  = self.glob_target(fpath, fn=self.sub_filter)
        for target in globbed:
            backup = target.with_suffix(f"{btarget.suffix}.backup")
            if not backup.exists():
                backup.write_text(btarget.read_text())
            # Format
            cmd = self.make_cmd("jq", "-M", "-S" , ".", target)
            # and save
            target.write_text(cmd.out)
