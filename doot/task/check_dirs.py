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
from doot.mixins.cleaning import CleanerMixin
from doot.task.base_tasker import DootTasker
from doot.task.base_task import DootTask

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@doot.check_protocol
class CheckDirTask(DootTask):
    """ A Task for checking a single location exists """

    def __init__(self, spec):
        super().__init__(spec)
        self.action_ctor = lambda x: partial(self.checkdir, x)

    def checkdir(self, target, task_state_copy):
        return target.exists()


@doot.check_protocol
class CheckDirTasker(DootTasker):
    """ Tasker for checking locations declared in toml exist """

    def __init__(self, locs:DootLocData|None=None):
        if isinstance(locs, DootTaskSpec):
            raise doot.errors.DootTaskError("CheckDirTasker has no need for a task spec")
        super().__init__(DootTaskSpec.from_dict({"name": "_locations::check"}))
        self.locs = locs or doot.locs

    def build(self, **kwargs) -> Generator[TaskBase_i]:
        head = self._build_head()
        for x in self.locs:
            loc = self.locs[x]
            sub = DootTaskSpec.from_dict({
                "name"    : self.fullname.subtask(x),
                "actions" : [loc],
                "ctor"    : CheckDirTask
                                         })
            head.runs_after.append(sub.name)
            yield sub

        yield head

    def mkdir(self):
        for _,x in self.locs:
            try:
                x.mkdir(parents=True)
                logging.info("Built Missing Location: %s", x)
            except FileExistsError:
                pass
