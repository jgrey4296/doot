#!/usr/bin/env python3
"""
Base classes for making tasks which glob over files / directories and make a subtask for each
matching thing
"""
##-- imports
from __future__ import annotations

from typing import Final
import enum
import logging as logmod
import pathlib as pl
import shutil
import warnings

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import doot
from doot.errors import DootDirAbsent
from doot.task.globber import DootEagerGlobber

@doot.check_protocol
class DootGeneraliser(DootEagerGlobber):
    """
    generaliser = DootGeneraliser("task::general.cat",
                                  locs=doot.locs,
                                  [doot.locs.src],
                                  taskers=[DootSingleFileCat])

    """

    def __init__(self, base:str, locs:DootLocData, roots:list[pl.Path], *, exts:list[str]=None,  rec=False, tasks=None, **kwargs):
        super().__init__(base, locs, roots, exts=exts, rec=rec, **kwargs)
        self.tasks = [] or tasks

    def _build_subtask(self, index, name, fpath) -> Generator[Task]:
        pass
