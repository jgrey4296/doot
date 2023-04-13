##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

import doot
from doot import tasker
from doot.mixins.commander import CommanderMixin

##-- end imports

from doot.mixins.gatgs import GtagsMixin
import doot
from doot.tasker import DootTasker
from doot.mixins.commander import CommanderMixin

class GtagsTask(DootTasker, GtagsMixin):

    def __init__(self, name="gtags::run", locs=None):
        super().__init__(name, locs)

    def task_detail(self, task):
        """([src]) initialise gtags """
        cmd_fn = self.gtags_update
        if self.args['gtags-init']
            cmd_fn = self.gtags_init

        task.update({
            "actions"  : [ self.cmd(cmd_fn, [self.locs.root]) ],
            "targets"  : [ self.locs.root / x for x in [ "GPATH", "GRTAGS", "GTAGS" ] ],
            "clean"    : True,
        })
        return task
