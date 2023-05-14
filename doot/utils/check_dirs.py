from __future__ import annotations

import logging as logmod
import pathlib as pl
import shutil
from typing import ClassVar

from doot.task.group import TaskGroup
from doot.mixins.cleaning import CleanerMixin

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doot.utils.task_namer import task_namer as namer

class CheckDir:
    """ Task for checking directories exist,
    making them if they don't
    """
    _all_registered : ClassVar[dict[str, CheckDir]] = {}
    _checker_basename = "locs::build"

    @staticmethod
    def as_taskgroup() -> TaskGroup:
        logging.debug("Building CheckDir Auto Tasks: %s", list(CheckDir._all_registered.keys()))
        return TaskGroup(CheckDir._checker_basename,
                         {
                             "basename" : namer(CheckDir._checker_basename),
                             "doc"      : ":: Build all locations for all registered location checks",
                             "actions"  : [],
                             "task_dep" : [x for x in CheckDir._all_registered.keys()],
                         },
                         *[x.build for x in CheckDir._all_registered.values()],
                         )

    def __init__(self, name="default", locs=None, private=True):
        self.base = CheckDir._checker_basename
        self.locs = locs
        self.name = name
        CheckDir._all_registered[namer(self.base, self.name, private=True)] = self

    def is_current(self):
        return all([y.exists() for x,y in self.locs])

    def build(self) -> dict:
        task = {
            "basename"  : self.base,
            "doc"       : ":: Build any missing directories in the loc",
            "name"      : self.name,
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
