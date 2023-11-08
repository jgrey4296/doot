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
from doot.structs import DootTaskSpec
from doot.task.globber import DootEagerGlobber

glob_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).setting.globbing.ignores()
glob_halts   : Final[str]  = doot.config.on_fail([".doot_ignore"], list).setting.globbing.halts()

@doot.check_protocol
class DootTreeShadower(DootEagerGlobber):
    """
      Glob a directory tree,
      but in addition to the subtask keys [`fpath`, `fstem`, `fname`, and `lpath`],
      the key `shadow_path` is added.

      The config key `shadow_root` is where a shadowed tree will start.
      eg:
      shadow_root : {data}/unpacked

      `shadow_path` is a path built onto the `shadow_root`, of the file's relation to its own glob root.
      eg:
      root        : {data}/packed
      fpath       : {data}/packed/bg2/raw/data/Scripts.bif
      lpath       : bg2/raw/data/Scripts.bif
      shadow_path : {shadow_root}/bg2/raw/data/Scripts.bif -> {data}/unpacked/bg2/raw/data/Scripts.bif

      To allow for easy saving of modified files, in a structure that mirrors the source data

      automatically includes `shadow_root` as a clean target
    """
    control = _GlobControl
    globc   = _GlobControl

    def __init__(self, spec:DootTaskSpec):
        super().__init__(spec)
        self.exts           = {y for x in spec.extra.on_fail([]).exts() for y in [x.lower(), x.upper()]}
        # expand roots based on doot.locs
        self.roots          = [doot.locs.get(x, fallback=pl.Path()) for x in spec.extra.on_fail([pl.Path()]).roots()]
        self.rec            = spec.extra.on_fail(False, bool).recursive()
        self.total_subtasks = 0
        for x in self.roots:
            depth = len(set(self.__class__.mro()) - set(DootEagerGlobber.mro()))
            if not x.exists():
                logging.warning(f"Globber Missing Root: {x.name}", stacklevel=depth)
            if not x.is_dir():
                 logging.warning(f"Globber Root is a file: {x.name}", stacklevel=depth)

    def _build_subs(self) -> Generator[DootTaskSpec]:
        self.total_subtasks = 0
        logging.debug("%s : Building Shadow SubTasks", self.name)
        for i, (uname, fpath) in enumerate(self.glob_all()):
            match self._build_subtask(i, uname, fpath=fpath, fstem=fpath.stem, fname=fpath.name, lpath=self.rel_path(fpath)):
                case None:
                    pass
                case DootTaskSpec() as subtask:
                    self.total_subtasks += 1
                    subtask.print_level = self.spec.extra.on_fail(subtask.print_level).sub_print_level()
                    yield subtask
                case _ as subtask:
                    raise TypeError("Unexpected type for subtask: %s", type(subtask))

    @classmethod
    def stub_class(cls, stub):
        stub.ctor                 = cls
        stub['version'].default   = cls._version
        stub['exts'].type         = "list[str]"
        stub['exts'].default      = []
        stub['roots'].type        = "list[str|pl.Path]"
        stub['roots'].default     = ["\".\""]
        stub['roots'].comment     = "Places the globber will start"
        stub['recursive'].type    = "bool"
        stub['recursive'].default = False
        stub['sub_print_level'].type = "str"
        stub['sub_print_level'].default = "WARN"

        return stub
