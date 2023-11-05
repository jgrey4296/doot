from __future__ import annotations

import logging as logmod
import pathlib as pl
import shutil
from typing import ClassVar
from functools import partial

import doot
import doot.errors
from doot.structs import DootStructuredName, DootTaskSpec
from doot._abstract import Tasker_i
from doot.mixins.task.cleaning import CleanerMixin
from doot.task.base_tasker import DootTasker
from doot.task.base_task import DootTask

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

make_missing = doot.config.on_fail(False).location_check.make_missing()
check_level  = doot.config.on_fail("WARN").location_check.print_level()

@doot.check_protocol
class CheckDirTask(DootTask):
    """ A Task for checking a single location exists """
    task_name = "_locations::check"

    def __init__(self, spec=None):
        locations = [[doot.locs[x]] for x in doot.locs]
        spec      = DootTaskSpec.from_dict({
            "name"        : CheckDirTask.task_name,
            "actions"     : locations,
                                           })
        super().__init__(spec, action_ctor=self.checkdir)

    def checkdir(self, spec, task_state_copy):
        exists_p = spec.args[0].exists()
        if exists_p:
            doot.printer.info("Base Location Exists : %s", spec.args[0])
        else:
            doot.printer.warning("Base Location Missing: %s", spec.args[0])
            if make_missing:
                doot.printer.info("Making Directory: %s", spec.args[0])
                spec.args[0].mkdir(parents=True)
        return
