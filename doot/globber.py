#!/usr/bin/env python3
"""
Base classes for making tasks which glob over files / directories and make a subtask for each
matching thing
"""
##-- imports
from __future__ import annotations

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

glob_ignores = doot.config.or_get(['.git', '.DS_Store', "__pycache__"], list).tool.doot.glob_ignores()

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

    def __init__(self, base:str, dirs:DootLocData, roots:list[pl.Path], *, exts:list[str]=None,  rec=False):
        super().__init__(base, dirs)
        self.exts              = (exts or [])[:]
        self.roots            = roots[:]
        self.rec               = rec
        self.total_subtasks    = 0
        for x in roots:
            if not pl.Path(x).exists():
                depth = len(set(self.__class__.mro()) - set(EagerFileGlobber.mro())) + 1
                warnings.warn(f"Globber Missing Root: {x}", stacklevel=depth)

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

    def glob_target(self, target, rec=False, fn=None, exts=None) -> list[pl.Path]:
        results   = []
        exts      = exts or self.exts or ["*"]
        filter_fn = fn or self.filter
        glob_fn   = target.rglob if (rec or self.rec) else target.glob

        for ext in [f"*{x}" if x[0] == "." else x for x in exts]:
            results += glob_fn(ext)

        results = [x for x in results if filter_fn(x) not in [False, GlobControl.reject, GlobControl.discard]]

        return results

    def glob_all(self, rec=False) -> list[tuple(pl.Path, str)]:
        """
        Glob all available files,
        and generate unique names for them
        """
        globbed = set()
        for root in self.roots:
            globbed.update(self.glob_target(root, rec=rec))

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

        return results.items()

    def _build_subs(self):
        globbed    = self.glob_all()
        setup_name = self._setup_names['full']
        subtasks   = []
        for i, (uname, fpath) in enumerate(self.glob_all()):
            subtask = self._build_subtask(i, uname, fpath=fpath)
            match (subtask, self.active_setup):
                case (None, _):
                    pass
                case (dict(), False):
                    subtasks.append(subtask)
                case (dict(), True):
                    subtask['setup'].append(self._setup_names['full'])
                    subtasks.append(subtask)
                case _:
                    raise TypeError("Unexpected type for subtask: %s", type(subtask))

        self.total_subtasks = len(subtasks)
        return subtasks

class EagerFileGlobber(DootEagerGlobber):
    pass

# Multiple Inheritances:
class DirGlobMixin:
    """
    Globs for directories instead of files.
    Generates a subtask for each found directory

    Recursive: all directories from roots down
    Non-Recursive: immediate subdirectories roots
    Always provides the root directories
    """

    def glob_files(self, target, rec=False, fn=None, exts=None):
        if fn is None:
            fn = lambda x: True
        return super().glob_target(target, rec=rec, fn=fn, exts=None)

    def glob_target(self, target, rec=False, fn=None, exts=None):
        results = []
        filter_fn = fn or self.filter
        if rec or self.rec:
            queue = [target]
            while bool(queue):
                current = queue.pop()
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

        else:
            results += [x for x in target.iterdir() if x.is_dir() and filter_fn(x) not in [False, GlobControl.reject, GlobControl.discard]]

        return results

class LazyGlobMixin:
    """
    Late globber, generates one subtask per root point,
    use self.glob_target to run the glob
    """

    def glob_all(self, rec=False):
        return [(str(x).replace("/", "_"), x) for x in self.roots]

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

    pass
