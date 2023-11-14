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

import random
import doot
from doot.errors import DootDirAbsent
from doot.task.dir_walker import DootDirWalker, _WalkControl
from doot.structs import DootTaskSpec

glob_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).setting.globbing.ignores()
glob_halts   : Final[str]  = doot.config.on_fail([".doot_ignore"], list).setting.globbing.halts()

@doot.check_protocol
class DootSubselectWalker(DootDirWalker):
    """
      Walk a directory,
      but instead of generating a task for every matching result,
      select only [num] by [method] matches,
      and generate tasks for them

    """
    control = _WalkControl
    globc   = _WalkControl

    def specialize_subtask(self, task) -> None|dict|DootTaskSpec:
        """
          use the task's data to look up a different task name to use, and modify the spec's ctor
        """
        raise NotImplementedError("TODO")

    def _build_subs(self) -> Generator[DootTaskSpec]:
        self.total_subtasks = 0
        logging.debug("%s : Building Subselection Walker SubTasks", self.name)
        filter_fn = self.import_class(self.spec.extra.on_fail((None,)).filter_fn())
        match_amnt = self.spec.extra.on_fail(0, int).select_num(int)
        matching = list(self.glob_all(fn=filter_fn))
        match spec.extra.on_fail("random", str).select_method():
            case "random":
                subselection = random.sample(matching, match_amnt)
            case _:
                raise doot.errors.DootTaskError("Bad Select Method specified")

        for i, (uname, fpath) in enumerate(subselection):
            match self._build_subtask(i, uname, fpath=fpath, fstem=fpath.stem, fname=fpath.name, lpath=self.rel_path(fpath)):
                case None:
                    pass
                case DootTaskSpec() as subtask:
                    self.total_subtasks += 1
                    yield subtask
                case _ as subtask:
                    raise TypeError("Unexpected type for subtask: %s", type(subtask))


    @classmethod
    def stub_class(cls, stub):
        stub.ctor                   = cls
        stub['version'].default     = cls._version
        stub['exts'].type           = "list[str]"
        stub['exts'].default        = []
        stub['roots'].type          = "list[str|pl.Path]"
        stub['roots'].default       = ["\".\""]
        stub['roots'].comment       = "Places the walker will start"
        stub['recursive'].type      = "bool"
        stub['recursive'].default   = False
        stub['select_num'].type     = "int"
        stub['select_num'].default  = 1
        stub['select_type'].type    = "str"
        stub['select_type'].default = "random"
        return stub
