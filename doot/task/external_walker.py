#!/usr/bin/env python3
"""
  Alternative walker using an external program, like fdfind
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

import sh
import doot
from doot.errors import DootDirAbsent
from doot.task.base_tasker import DootTasker
from doot.mixins.tasker.subtask import SubMixin
from doot.structs import DootTaskSpec

walk_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).settings.walking.ignores()
walk_halts   : Final[str]  = doot.config.on_fail([".doot_ignore"], list).settings.walking.halts()


@doot.check_protocol
class DootExternalWalker(SubMixin, DootTasker):
    """
    Base tasker for using an external program for finding files to operate on
    """

    def __init__(self, spec:DootTaskSpec):
        super().__init__(spec)
        self.exts           = {y for x in spec.extra.on_fail([]).exts() for y in [x.lower(), x.upper()]}
        # expand roots based on doot.locs
        self.roots          = [doot.locs.get(x, fallback=pl.Path()) for x in spec.extra.on_fail([pl.Path()]).roots()]
        self.total_subtasks = 0
        for x in self.roots:
            depth = len(set(self.__class__.mro()) - set(super().__class__.mro()))
            if not x.exists():
                logging.warning(f"Walker Missing Root: {x.name}", stacklevel=depth)
            if not x.is_dir():
                 logging.warning(f"Walker Root is a file: {x.name}", stacklevel=depth)

    def filter(self, target:pl.Path) -> bool:
        """ filter function called on each prospective glob result
        override in subclasses as necessary
        """
        return True

    def rel_path(self, fpath) -> pl.Path:
        """
        make the path relative to the appropriate root
        """
        for root in self.roots:
            try:
                return fpath.relative_to(root)
            except ValueError:
                continue

        raise ValueError(f"{fpath} is not able to be made relative")

    def build(self, **kwargs) -> Generator[DootTaskSpec]:
        head = self._build_head()

        for sub in self._build_subs():
            head.depends_on.append(sub.name)
            yield sub

        yield head

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

    def glob_all(self, fn=None) -> Generator[tuple(str, pl.Path)]:
        """
          run the spec's `cmd`, expanded with `exts`, for each entry in `roots`
          combine, and return
        """
        base_name     = self.fullname
        globbed_names = set()
        cmd           = sh.Command(self.spec.extra.cmd)
        baked         = cmd.bake(*self.spec.extra.cmd_args)
        for root in self.roots:
            results = baked(root)
            for fpath in results:
                # ensure unique task names
                curr = fpath.absolute()
                name = base_name.subtask(curr.stem)
                logging.debug("Building Unique name for: %s : %s", name, fpath)
                while name in globbed_names:
                    curr = curr.parent
                    name = name.subtask(curr.stem)

                globbed_names.add(name)
                yield name, fpath

    @classmethod
    def stub_class(cls, stub):
        stub.ctor                 = cls
        stub['version'].default   = cls._version
        stub['roots'].type        = "list[str|pl.Path]"
        stub['roots'].default     = ["\".\""]
        stub['roots'].comment     = "Places the walker will start"
        stub['exts'].type         = "list[str]"
        stub['exts'].default      = []
        stub['exts'].prefix       = "# "
        stub["filter_fn"].type    = "callable"
        stub['filter_fn'].prefix  = "# "
        stub['cmd'].type          = "string"
        stub['cmd'].default       = "fdfind"
        stub['cmd_args'].type     = "list[str]"
        stub['cmd_args'].default  = ['--color', 'never']
        return stub
