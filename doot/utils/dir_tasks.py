
##-- imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
import shutil
from typing import ClassVar

from doot.task_group import TaskGroup
from doot.tasker import DootTasker
from doot.utils.cleaning import CleanerMixin
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class CheckDir:
    """ Task for checking directories exist,
    making them if they don't
    """
    _all_registered : ClassVar[dict[str, CheckDir]] = {}
    _checker_name = "_locs::check"

    @staticmethod
    def gen_check_tasks():
        logging.debug("Building CheckDir Auto Tasks: %s", list(CheckDir._all_registered.keys()))
        return TaskGroup(CheckDir._checker_name,
                         {
                             "basename" : "locs::build",
                             "doc"      : ":: Build all locations for all registered location checks",
                             "actions"  : [],
                             "task_dep" : [x for x in CheckDir._all_registered.keys()],
                         },
                         *CheckDir._all_registered.values(),
                         as_creator=True)

    def __init__(self, name="default", locs=None, private=True):
        self.base = name
        self.locs = locs
        self.name = f"{CheckDir._checker_name}:{self.base}"
        CheckDir._all_registered[self.name] = self

    def is_current(self):
        return all([y.exists() for x,y in self.locs])

    def build_check(self) -> dict:
        task = {
            "name"      : self.base,
            "actions"   : [ self.mkdir ],
            "clean"     : [ CleanerMixin.clean_target_dirs ],
            "uptodate"  : [ self.is_current ],
            "verbosity" : 2,
        }
        return task

    def mkdir(self):
        for _,x in self.locs:
            try:
                x.mkdir(parents=True)
                logging.info("Built Missing Location: %s", x)
            except FileExistsError:
                pass

