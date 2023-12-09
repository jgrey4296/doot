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

printer = logmod.getLogger("doot._printer")

import doot
from doot.errors import DootDirAbsent
from doot.task.dir_walker import DootDirWalker, _WalkControl
from doot.structs import DootTaskSpec

walk_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).settings.walking.ignores()
walk_halts   : Final[str]  = doot.config.on_fail([".doot_ignore"], list).settings.walking.halts()

@doot.check_protocol
class DootPatternWalker(DootDirWalker):
    """
    Base tasker for file based directory walking.
      Instead of globbing, uses regex matching.
    Generates a new subtask for each file found.

    Each File found is a separate subtask

    """
    control = _WalkControl
    globc   = _WalkControl

    def specialize_subtask(self, task) -> None|dict|DootTaskSpec:
        """
          use the task's data to look up a different task name to use, and modify the spec's ctor
        """
        raise NotImplementedError("TODO")



    @classmethod
    def stub_class(cls, stub):
        stub.ctor                 = cls
        stub['version'].default   = cls._version
        stub['exts'].type         = "list[str]"
        stub['exts'].default      = []
        stub['roots'].type        = "list[str|pl.Path]"
        stub['roots'].default     = ["\".\""]
        stub['roots'].comment     = "Places the walker will start"
        stub['recursive'].type    = "bool"
        stub['recursive'].default = False
        return stub
