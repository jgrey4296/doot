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

walk_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).settings.walking.ignores()
walk_halts   : Final[str]  = doot.config.on_fail([".doot_ignore"], list).settings.walking.halts()

class _WalkControl(enum.Enum):
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
class DootDirWalker(SubMixin, DootTasker):
    """
    Base tasker for file based globbing.
    Each File found is a separate subtask

    Uses the toml key `sub_task` to spec each task,
    and `head_task` for a final task to run after all subtasks finish

    Each Subtask gets keys added to its state: [fpath, fstem. fname, lpath]
    `exts` filters by extension (py-style, so eg: '.bib')
    `roots` defines starting locations.
    `recursive` controls if just the specified location is searched, or subdirs.
    `filter_fn` allows an import path of a callable: lambda(pl.Path) -> _WalkControl

    Config files can specify:
    settings.walking.ignores = []
    settings.walking.halts   = []

    Override as necessary:
    .filter : for controlling glob results
    .glob_target : for what is globbed
    .{top/subtask/setup/teardown}_detail : for controlling task definition
    .{top/subtask/setup/teardown}_actions : for controlling task actions
    .default_task : the basic task definition that everything customises
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

    def filter(self, target:pl.Path) -> bool | _WalkControl:
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
        printer.info("Walking Target: %s : rec=%s, exts=%s", target, rec, exts)

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
            if current.name in walk_ignores:
                continue
            if current.is_dir() and any([(current / x).exists() for x in walk_halts]):
                continue
            if bool(exts) and current.is_file() and current.suffix not in exts:
                continue
            match filter_fn(current):
                case _WalkControl.keep | _WalkControl.yes:
                    yield current
                case True if current.is_dir():
                    queue += sorted(current.iterdir())
                case True | _WalkControl.accept | _WalkControl.yesAnd:
                    yield current
                    if current.is_dir():
                        queue += sorted(current.iterdir())
                case False | _WalkControl.discard | _WalkControl.noBut if current.is_dir():
                    queue += sorted(current.iterdir())
                case None | False:
                    continue
                case _WalkControl.reject | _WalkControl.discard:
                    continue
                case _WalkControl.no | _WalkControl.noBut:
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

    def _non_recursive_glob(self, target, filter_fn, exts):
        check_fn = lambda x: (filter_fn(x) not in [None, False, _WalkControl.reject, _WalkControl.discard, _WalkControl.no, _WalkControl.noBut]
                                and x.name not in walk_ignores
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
        stub['roots'].type        = "list[str|pl.Path]"
        stub['roots'].default     = ["\".\""]
        stub['roots'].comment     = "Places the walker will start"
        stub['exts'].type         = "list[str]"
        stub['exts'].default      = []
        stub['exts'].prefix       = "# "
        stub['recursive'].type    = "bool"
        stub['recursive'].default = False
        stub['recursive'].prefix  = "# "
        stub["filter_fn"].type    = "callable"
        stub['filter_fn'].prefix  = "# "
        return stub
