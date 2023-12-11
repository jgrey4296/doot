#!/usr/bin/env python3
"""
Base classes for making tasks which walk over files / directories and make a subtask for each
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
from doot.errors import DootDirAbsent, DootLocationError
from doot.structs import DootTaskSpec
from doot.task.dir_walker import DootDirWalker, _WalkControl

walk_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).settings.walking.ignores()
walk_halts   : Final[str]  = doot.config.on_fail([".doot_ignore"], list).settings.walking.halts()

@doot.check_protocol
class DootTreeShadower(DootDirWalker):
    """
      Walk a directory tree,
      but in addition to the subtask keys [`fpath`, `fstem`, `fname`, and `lpath`],
      the key `shadow_path` is added.
      Combining `shadow_path` with `fname` gives a full file path

      raises doot.errors.DootLocationError if the shadowed path is the same as the original

      The config key `shadow_root` is where a shadowed tree will start.
      eg:
      shadow_root : {data}/unpacked

      `shadow_path` is a path built onto the `shadow_root`, of the file's relation to its own walk root.
      eg:
      root        : {data}/packed
      fpath       : {data}/packed/bg2/raw/data/Scripts.bif
      lpath       : bg2/raw/data/Scripts.bif
      shadow_path : {shadow_root}/bg2/raw/data/ -> {data}/unpacked/bg2/raw/data/

      To allow for easy saving of modified files, in a structure that mirrors the source data

      automatically includes `shadow_root` as a clean target
    """
    control = _WalkControl

    def __init__(self, spec:DootTaskSpec):
        super().__init__(spec)
        self.exts           = {y for x in spec.extra.on_fail([]).exts() for y in [x.lower(), x.upper()]}
        # expand roots based on doot.locs
        self.roots          = [doot.locs.get(x, fallback=pl.Path()) for x in spec.extra.on_fail([pl.Path()]).roots()]
        self.rec            = spec.extra.on_fail(False, bool).recursive()
        self.total_subtasks = 0
        for x in self.roots:
            depth = len(set(self.__class__.mro()) - set(super().__class__.mro()))
            if not x.exists():
                logging.warning(f"Walker Missing Root: {x.name}", stacklevel=depth)
            if not x.is_dir():
                 logging.warning(f"Walker Root is a file: {x.name}", stacklevel=depth)

    def _build_subs(self) -> Generator[DootTaskSpec]:
        self.total_subtasks = 0
        logging.debug("%s : Building Shadow SubTasks", self.name)
        for i, (uname, fpath) in enumerate(self.walk_all()):
            match self._build_subtask(i, uname,
                                      fpath=fpath,
                                      fstem=fpath.stem,
                                      fname=fpath.name,
                                      lpath=self.rel_path(fpath),
                                      shadow_path=self._shadow_path(fpath)):
                case None:
                    pass
                case DootTaskSpec() as subtask:
                    self.total_subtasks += 1
                    yield subtask
                case _ as subtask:
                    raise TypeError("Unexpected type for subtask: %s", type(subtask))

    def _shadow_path(self, fpath:pl.Path) -> pl.Path:
        shadow_root = doot.locs[self.spec.extra.shadow_root]
        rel_path    = self.rel_path(fpath)
        result      = shadow_root / rel_path
        if result == fpath:
            raise DootLocationError("Shadowed Path is same as original", fpath)

        return result.parent


    @classmethod
    def stub_class(cls, stub):
        stub.ctor = cls
        stub['shadow_root'].type = "Path"
        stub['shadow_root'].default = ""
        return stub
