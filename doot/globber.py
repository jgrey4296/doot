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

from doit.action import CmdAction
from doit.task import dict_to_task

import doot
from doot.errors import DootDirAbsent
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doot.tasker import DootTasker
from doot.mixins.subtask import SubMixin

glob_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).globbing.ignores()
glob_halts   : Final[str]  = doot.config.on_fail([".doot_ignore"], list).globbing.halts()

class GlobControl(enum.Enum):
    """
    accept  : is a result, and descend if recursive
    keep    : is a result, don't descend
    discard : not a result, descend
    reject  : not a result, don't descend
    """
    accept  = enum.auto()
    yesAnd  = enum.auto()

    keep    = enum.auto()
    yes     = enum.auto()

    discard = enum.auto()
    noBut   = enum.auto()

    reject  = enum.auto()
    no      = enum.auto()


class DootEagerGlobber(SubMixin, DootTasker):
    """
    Base task for file based *on load* globbing.
    Generates a new subtask for each file found.

    Each File found is a separate subtask

    Override as necessary:
    .filter : for controlling glob results
    .glob_target : for what is globbed
    .{top/subtask/setup/teardown}_detail : for controlling task definition
    .{top/subtask/setup/teardown}_actions : for controlling task actions
    .default_task : the basic task definition that everything customises
    """
    control = GlobControl
    globc   = GlobControl

    def __init__(self, base:str, locs:DootLocData, roots:list[pl.Path], *, exts:list[str]=None,  rec=False, **kwargs):
        super().__init__(base, locs, **kwargs)
        self.exts           = {y for x in (exts or []) for y in [x.lower(), x.upper()]}
        self.roots          = roots[:]
        self.rec            = rec
        self.total_subtasks = 0
        for x in roots:
            try:
                if not pl.Path(x).exists():
                    depth = len(set(self.__class__.mro()) - set(DootEagerGlobber.mro()))
                    warnings.warn(f"Globber Missing Root: {x}", stacklevel=depth)
            except TypeError as err:
                breakpoint()
                pass

    def filter(self, target:pl.Path) -> bool | GlobControl:
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

    def glob_target(self, target, rec=None, fn=None, exts=None) -> Generator[pl.Path]:
        exts      = exts or self.exts or []
        filter_fn = fn or self.filter

        if not target.exists():
            yield from []
            return None

        if not (bool(rec) or rec is None and self.rec):
            check_fn = lambda x: (filter_fn(x) not in [None, False, GlobControl.reject, GlobControl.discard]
                                  and x.name not in glob_ignores
                                  and (not bool(exts) or (x.is_file() and x.suffix in exts)))

            if check_fn(target):
                yield target

            if not target.is_dir():
                return None

            for x in target.iterdir():
                if check_fn(x):
                    yield x

            return None

        assert(rec or self.rec)
        queue = [target]
        while bool(queue):
            current = queue.pop()
            if not current.exists():
                continue
            if current.name in glob_ignores:
                continue
            if current.is_dir() and any([(current / x).exists() for x in glob_halts]):
                continue
            if bool(exts) and current.is_file() and current.suffix not in exts:
                continue
            match filter_fn(current):
                case GlobControl.keep | GlobControl.yes:
                    yield current
                case False | GlobControl.discard | GlobControl.noBut if current.is_dir():
                    queue += sorted(current.iterdir())
                case True | GlobControl.accept | GlobControl.yesAnd:
                    yield current
                    if current.is_dir():
                        queue += sorted(current.iterdir())
                case None | False:
                    continue
                case GlobControl.reject | GlobControl.discard:
                    continue
                case GlobControl.no | GlobControl.noBut:
                    continue
                case _ as x:
                    raise TypeError("Unexpected glob filter value", x)


    def glob_all(self, rec=None, fn=None) -> Generator[tuple(str, pl.Path)]:
        """
        Glob all available files,
        and generate unique names for them
        """
        globbed_count = 0
        globbed_names = set()
        for root in self.roots:
            for fpath in self.glob_target(root, rec=rec, fn=fn):
                parts = list(fpath.parts[:-1]) + [fpath.stem]

                # ensure unique task names
                index = len(parts) - 2
                while 0 < index and "_".join(parts[index:]) in globbed_names:
                    index -= 1

                unique_name = "_".join(parts[index:])
                globbed_names.add(unique_name)
                yield unique_name, fpath

        logging.debug("Globbed : %s", globbed_count)

    def _build_subs(self) -> Generator[dict]:
        self.total_subtasks = 0
        logging.debug("%s : Building Globber SubTasks", self.basename)
        for i, (uname, fpath) in enumerate(self.glob_all()):
            match self._build_subtask(i, uname, fpath=fpath):
                case None:
                    pass
                case dict() as subtask:
                    self.total_subtasks += 1
                    yield subtask
                case _:
                    raise TypeError("Unexpected type for subtask: %s", type(subtask))
