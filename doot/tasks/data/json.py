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
from doot.mixins.json import JsonMixin

class JsonFormatTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, FilerMixin, CommanderMixin, JsonMixin):
    """
    ([data] -> data) Lint Json files with jq *inplace*
    """

    def __init__(self, name="json::format.inplace", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".json"], rec=rec)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_file() and fpath.suffix in self.exts:
            return self.globc.yes
        return self.globc.noBut

    def subtask_detail(self, task, fpath=None):
        task.update({
            "uptodate" : [False],
            "actions" : [
                self.make_cmd(self.json_filter, [fpath], save="formatted"),
                (self.write_to, [fpath, "formatted"]),
                ],
            })
        return task
