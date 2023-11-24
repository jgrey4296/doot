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
from doot.task.base_tasker import DootTasker
from doot.mixins.tasker.subtask import SubMixin
from doot.structs import DootTaskSpec
from doot.task.dir_walker import DootDirWalker, _WalkControl

walk_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).settings.walking.ignores()
walk_halts   : Final[str]  = doot.config.on_fail([".doot_ignore"], list).settings.walking.halts()


@doot.check_protocol
class DootWalkMapper(DootDirWalker):
    """
      A Customized walker which uses the `sub_task` key as a default subtask,
      and specializes subtasks uses a `sub_map` dictionary.

      sub_map = {
      ".bib"  :  "files::bib",
      ".json" :  "files::json",
      }

       so {data}/1252.bib -> files::bib
          {data}/blah.json -> files::json
       but {data}/scripts.bif -> {sub_task}

    """
    control = _WalkControl
    globc   = _WalkControl

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
        logging.debug("%s : Building Walker SubTasks", self.name)
        filter_fn = self.import_class(self.spec.extra.on_fail((None,)).filter_fn())
        for i, (uname, fpath) in enumerate(self.glob_all(fn=filter_fn)):
            match self._build_subtask(i, uname, fpath=fpath, fstem=fpath.stem, fname=fpath.name, lpath=self.rel_path(fpath)):
                case None:
                    pass
                case DootTaskSpec() as subtask:
                    self.total_subtasks += 1
                    yield subtask
                case _ as subtask:
                    raise TypeError("Unexpected type for subtask: %s", type(subtask))

    def specialize_subtask(self, task) -> None|dict|DootTaskSpec:
        # lookup using spec keys
        # task_spec.ctor_name = DootStructuredName.from_str(val)
        return task

    @classmethod
    def stub_class(cls, stub):
        stub.ctor                 = cls
        stub['version'].default   = cls._version
        stub['exts'].type         = "list[str]"
        stub['exts'].default      = []
        stub['exts'].prefix = "# "
        stub['roots'].type        = "list[str|pl.Path]"
        stub['roots'].default     = ["\".\""]
        stub['roots'].comment     = "Places the walker will start"
        stub['recursive'].type    = "bool"
        stub['recursive'].default = False
        stub['recursive'].prefix = "# "
        stub["filter_fn"].type = "callable"
        stub["filter_fn"].default = ""
        stub['filter_fn'].prefix = "# "
        return stub
