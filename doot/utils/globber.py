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
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.tasker import DootSubtasker
from doot.errors import DootDirAbsent
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

glob_ignores = doot.config.or_get(['.git', '.DS_Store', "__pycache__"]).tool.doot.glob_ignores()

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




class EagerFileGlobber(DootSubtasker):
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
                warnings.warn(f"Globber Missing Root: {x}")


    def filter(self, target:pl.Path) -> bool | GlobControl:
        """ filter function called on each prospective glob result
        override in subclasses as necessary
        """
        return True

    def glob_target(self, target, rec=False, fn=None) -> list[pl.Path]:
        results = []
        exts    = self.exts or [".*"]
        filter_fn = fn or self.filter
        glob_fn = target.rglob if (rec or self.rec) else target.glob

        for ext in exts:
            results += list(glob_fn("*"+ext))

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

    def _build_task(self, **kwargs):
        """
        Generalized task builder for globbing on files
        then customizing the subtasks
        """
        self.params.update(kwargs)
        subtasks = []
        globbed  = self.glob_all()
        subtasks_names = []
        for i, (uname, fpath) in enumerate(self.glob_all()):
            subtask = self._build_subtask(i, uname, fpath=fpath)
            if subtask is not None:
                subtasks_names.append(subtask['name'])
                subtasks.append(subtask)

        subtasks.append(self._build_setup())

        top_task = self.default_task()
        top_task.update({
            "task_dep" : [f"{self.base}:{x}" for x in subtasks_names],
        })
        detailed = self.task_detail(top_task)
        if detailed is not None:
            yield detailed

        self.total_subtasks = len(subtasks)

        for sub in subtasks:
            if sub is not None:
                yield sub



class DirGlobber(EagerFileGlobber):
    """
    Globs for directories instead of files.
    Generates a subtask for each found directory

    Recursive: all directories from roots down
    Non-Recursive: immediate subdirectories roots
    Always provides the root directories
    """
    def glob_files(self, target, rec=False, fn=None):
        if fn is None:
            fn = lambda x: True
        return super().glob_target(target, rec=rec, fn=fn)


    def glob_target(self, target, rec=False, fn=None):
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




class LazyFileGlobber(EagerFileGlobber):
    """
    Late globber, generates one subtask per root point,
    use self.glob_target to run the glob
    """

    def glob_all(self, rec=False):
        return [(str(x).replace("/", "_"), x) for x in self.roots]

class HeadlessFileGlobber(EagerFileGlobber):
    """
    Glob for files, but don't provide a top level task to
    run all of them together
    """

    def _build_task(self, **kwargs):
        """
        Generalized task builder for globbing on files
        then customizing the subtasks
        """
        self.params.update(kwargs)
        subtasks = []
        globbed = self.glob_all()
        for i, (uname, fpath) in enumerate(self.glob_all()):
            subtask = self._build_subtask(i, uname, fpath=fpath)
            if subtask is not None:
                subtasks.append(subtask)

        subtasks.append(self._build_setup())

        top_task = self.default_task()
        subtasks.append(self.top_detail(top_task))

        self.total_subtasks = len(subtasks)

        for sub in subtasks:
            if sub is not None:
                yield sub
