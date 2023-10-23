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
from doot.mixins.subtask import SubMixin
from doot.structs import DootTaskSpec

glob_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).globbing.ignores()
glob_halts   : Final[str]  = doot.config.on_fail([".doot_ignore"], list).globbing.halts()

class _GlobControl(enum.Enum):
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

@doot.check_protocol
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
    control = _GlobControl
    globc   = _GlobControl

    def __init__(self, spec:DootTaskSpec):
        super().__init__(spec)
        self.exts           = {y for x in spec.extra.on_fail([]).exts() for y in [x.lower(), x.upper()]}
        # TODO expand roots based on doot.locs
        self.roots          = [pl.Path(x) for x in spec.extra.on_fail([pl.Path()]).roots()]
        self.rec            = spec.extra.on_fail(False, bool).recursive()
        self.total_subtasks = 0
        for x in self.roots:
            depth = len(set(self.__class__.mro()) - set(DootEagerGlobber.mro()))
            if not x.exists():
                logging.warning(f"Globber Missing Root: {x}", stacklevel=depth)
            if not x.is_dir():
                 logging.warning(f"Globber Root is a file: {x}", stacklevel=depth)

    def filter(self, target:pl.Path) -> bool | _GlobControl:
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
        rec       = bool(rec) or rec is None and self.rec
        exts      = exts or self.exts or []
        filter_fn = fn or self.filter
        printer.debug("Globbing on Target: %s : rec=%s, exts=%s", target, rec, exts)

        if not target.exists():
            return None

        if not rec:
            yield from self._non_recursive_glob(target, filter_fn, exts)
            return None

        assert(rec)
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
                case _GlobControl.keep | _GlobControl.yes:
                    yield current
                case True if current.is_dir() and bool(exts):
                    queue += sorted(current.iterdir())
                case True | _GlobControl.accept | _GlobControl.yesAnd:
                    yield current
                    if current.is_dir():
                        queue += sorted(current.iterdir())
                case False | _GlobControl.discard | _GlobControl.noBut if current.is_dir():
                    queue += sorted(current.iterdir())
                case None | False:
                    continue
                case _GlobControl.reject | _GlobControl.discard:
                    continue
                case _GlobControl.no | _GlobControl.noBut:
                    continue
                case _ as x:
                    raise TypeError("Unexpected glob filter value", x)

    def glob_all(self, rec=None, fn=None) -> Generator[tuple(str, pl.Path)]:
        """
        Glob all available files,
        and generate unique names for them
        """
        base_name = self.fullname
        globbed_names = set()
        for root in self.roots:
            for fpath in self.glob_target(root, rec=rec, fn=fn):
                # ensure unique task names
                curr = fpath.absolute()
                name = base_name.subtask(curr.stem)
                logging.debug("Building Unique name for: %s : %s", name, fpath)
                while name in globbed_names:
                    curr = curr.parent
                    name = name.subtask(curr.stem)

                globbed_names.add(name)
                yield name, fpath

        logging.debug("Globbed : %s", len(globbed_names))

    def build(self, **kwargs) -> Generator[DootTaskSpec]:
        self.args.update(kwargs)
        head = self._build_head()

        for sub in self._build_subs():
            head.runs_after.append(sub.name)
            yield sub

        yield head

    def _build_subs(self) -> Generator[DootTaskSpec]:
        self.total_subtasks = 0
        logging.debug("%s : Building Globber SubTasks", self.name)
        for i, (uname, fpath) in enumerate(self.glob_all()):
            match self._build_subtask(i, uname, fpath=fpath):
                case None:
                    pass
                case DootTaskSpec() as subtask:
                    self.total_subtasks += 1
                    yield subtask
                case _ as subtask:
                    raise TypeError("Unexpected type for subtask: %s", type(subtask))

    def _non_recursive_glob(self, target, filter_fn, exts):
        check_fn = lambda x: (filter_fn(x) not in [None, False, _GlobControl.reject, _GlobControl.discard]
                                and x.name not in glob_ignores
                                and (not bool(exts) or (x.is_file() and x.suffix in exts)))

        if check_fn(target):
            yield target

        if not target.is_dir():
            return None

        for x in target.iterdir():
            if check_fn(x):
                yield x


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
        return stub
