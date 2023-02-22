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
from doot.tasker import DootSubtasker
from doot.errors import DootDirAbsent
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import random

glob_ignores          : Final = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).tool.doot.globbing.ignores()
glob_subselect_exact  : Final = doot.config.on_fail(10, int).tool.doot.globbing.subselect_exact()
glob_subselect_pcnt   : Final = doot.config.on_fail(0, int).tool.doot.globbing.subselect_percentage()

class GlobControl(enum.Enum):
    """
    accept  : is a result, and descend if recursive
    keep    : is a result, don't descend
    discard : not a result, descend
    reject  : not a result, don't descend
    """
    accept  = enum.auto()
    keep    = enum.auto()
    discard = enum.auto()
    reject  = enum.auto()

class DootEagerGlobber(DootSubtasker):
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

    def glob_target(self, target, rec=None, fn=None, exts=None) -> list[pl.Path]:
        results   = []
        exts      = exts or self.exts or []
        filter_fn = fn or self.filter

        if not target.exists():
            return []
        elif not (bool(rec) or rec is None and self.rec):
            check_fn = lambda x: (filter_fn(x) not in [False, GlobControl.reject, GlobControl.discard]
                                  and x.name not in glob_ignores
                                  and not (bool(exts) and x.is_file() and x.suffix not in exts))

            potentials  = [target] + [x for x in target.iterdir()]
            results     = [x for x in potentials if check_fn(x)]
            return results

        assert(rec or self.rec)
        queue = [target]
        while bool(queue):
            current = queue.pop()
            if not current.exists():
                continue
            if current.name in glob_ignores:
                continue
            if bool(exts) and current.is_file() and current.suffix not in exts:
                continue
            match filter_fn(current):
                case GlobControl.keep:
                    results.append(current)
                case GlobControl.discard if current.is_dir():
                    queue += [x for x in current.iterdir()]
                case True | GlobControl.accept:
                    results.append(current)
                    if current.is_dir():
                        queue += [x for x in current.iterdir()]
                case None | False | GlobControl.reject | GlobControl.discard:
                    continue
                case _ as x:
                    raise TypeError("Unexpected glob filter value", x)

        return results

    def glob_all(self, rec=None, fn=None) -> list[tuple(str, pl.Path)]:
        """
        Glob all available files,
        and generate unique names for them
        """
        globbed = set()
        for root in self.roots:
            globbed.update(self.glob_target(root, rec=rec, fn=fn))

        results = {}
        # then create unique names based on path:
        for fpath in globbed:
            parts = list(fpath.parts[:-1]) + [fpath.stem]
            if "_".join(parts[-2:]) not in results:
                results["_".join(parts[-2:])] = fpath
                continue

            # name already exists, create a unique version
            # based on its path
            index = len(parts) - 2
            while "_".join(parts[index:]) in results:
                index -= 1

            results["_".join(parts[index:])] = fpath

        return list(results.items())

    def _build_subs(self):
        globbed    = self.glob_all()
        subtasks   = []
        for i, (uname, fpath) in enumerate(self.glob_all()):
            subtask = self._build_subtask(i, uname, fpath=fpath)
            match subtask:
                case None:
                    pass
                case dict():
                    subtasks.append(subtask)
                case _:
                    raise TypeError("Unexpected type for subtask: %s", type(subtask))

        self.total_subtasks = len(subtasks)
        return subtasks

# Multiple Inheritances:

class DirGlobMixin:
    """
    Globs for directories instead of files.
    Generates a subtask for each found directory

    Recursive: all directories from roots down
    Non-Recursive: immediate subdirectories roots
    Always provides the root directories
    """

    def glob_files(self, target, rec=None, fn=None, exts=None):
        if fn is None:
            fn = lambda x: True
        return super().glob_target(target, rec=rec, fn=fn, exts=exts)

    def glob_target(self, target, rec=None, fn=None, exts=None):
        results = []
        filter_fn = fn or self.filter
        if not target.exists():
            return []
        elif not (rec or self.rec):
            if filter_fn(target) not in [False, GlobControl.reject, GlobControl.discard]:
                results.append(target)
            results += [x for x in target.iterdir() if x.is_dir() and filter_fn(x) not in [False, GlobControl.reject, GlobControl.discard]]
            return results

        assert(rec or self.rec)
        queue = [target]
        while bool(queue):
            current = queue.pop()
            if not current.exists():
                continue
            if current.name in glob_ignores:
                continue
            if current.is_file():
                continue
            match filter_fn(current):
                case GlobControl.keep:
                    results.append(current)
                case GlobControl.discard:
                    queue += [x for x in current.iterdir() if x.is_dir()]
                case True | GlobControl.accept:
                    results.append(current)
                    queue += [x for x in current.iterdir() if x.is_dir()]
                case None | False | GlobControl.reject:
                    continue
                case _ as x:
                    raise TypeException("Unexpected glob filter value", x)

        return results

class LazyGlobMixin:
    """
    Late globber, generates one subtask per root point,
    use self.glob_target to run the glob
    """

    def __init__(self, *args, **kwargs):
        raise DeprecationWarning("Use The DelayedMixin")

    def glob_all(self, root=None, rec=None, fn=None):
        # return [(str(x).replace("/", "_"), x) for x in self.roots]
        return []

class HeadlessGlobMixin:
    """
    Glob for files, but don't provide a top level task to
    run all of them together
    """

    def _build_task(self, **kwargs):
        """
        Generalized task builder for globbing on files
        then customizing the subtasks
        """
        return super(DootSubtasker, self)._build_task()

class SubGlobMixin:
    """
    Glob only a subset of potentials
    """

    def glob_all(self, rec=None, fn=None):
        results = super().glob_all(rec)
        match glob_subselect_exact, glob_subselect_pcnt:
            case (-1, -1):
                return results
            case exact, 0:
                k = min(exact, len(results))
            case 0, percent:
                one = len(results) * 0.01
                k = int(one * percent)

        return random.choices(results, k=k)
