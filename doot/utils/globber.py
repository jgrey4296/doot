#!/usr/bin/env python3
"""
Base classes for making tasks which glob over files / directories and make a subtask for each
matching thing
"""
##-- imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
import shutil

from doit.action import CmdAction
from doot import data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.tasker import DootSubtasker
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


class FileGlobberMulti(DootSubtasker):
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

    def __init__(self, base:str, dirs:DirData, roots:list[pl.Path], *, exts:list[str]=None,  rec=False):
        super().__init__(base, dirs)
        self.exts              = (exts or [])[:]
        self.roots            = roots[:]
        self.rec               = rec
        self.total_subtasks    = 0

    def filter(self, target:pl.Path):
        """ filter function called on each prospective glob result
        override in subclasses as necessary
        """
        return True

    def glob_target(self, target, rec=False):
        results = []
        if rec or self.rec:
            for ext in self.exts:
                results += list(target.rglob("*"+ext))
        else:
            for ext in self.exts:
                results += list(target.glob("*"+ext))

        results = [x for x in results if self.filter(x)]

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

    def subtask_actions(self, fpath) -> list[str|CmdAction|Callable]:
        return [f"echo {fpath}"]

    def subtask_detail(self, fpath:pl.Path, task:dict) -> None|dict:
        """
        override to add any additional task details
        """
        return task

    def setup_detail(self, task:dict) -> None|dict:
        return task
    def teardown_detail(self, task:dict) -> None|dict:
        return task

    def top_detail(self, task:dict) -> None|dict:
        return task
    def _build_tasks(self):
        """
        Generalized task builder for globbing on files
        then customizing the subtasks
        """
        subtasks = []
        globbed  = self.glob_all()
        for i, (uname, fpath) in enumerate(self.glob_all()):
            subtask = self._build_subtask(i, uname, fpath)
            if subtask is not None:
                subtasks.append(subtask)

        subtasks.append(self._build_teardown([f"{x['basename']}:{x['name']}" for x in subtasks]))
        subtasks.append(self._build_setup())

        top_task = self.default_task()
        top_task.update({
            "task_dep" : [f"_{self.base}:post"],
        })
        subtasks.append(self.top_detail(top_task))

        self.total_subtasks = len(subtasks)

        for sub in subtasks:
            if sub is not None:
                yield sub



class DirGlobber(FileGlobberMulti):
    """
    Globs for directories instead of files.
    Generates a subtask for each found directory

    Recursive: all directories from roots down
    Non-Recursive: immediate subdirectories roots
    Always provides the root directories
    """

    def glob_target(self, target, rec=False):
        results = [target]
        if rec or self.rec:
            queue = list(target.iterdir())
            while bool(queue):
                current = queue.pop()
                if current.is_file():
                    continue

                contents = list(current.iterdir())
                if not bool(contents):
                    # no contents, ignore
                    continue

                results.append(current)
                queue += [x for x in contents if x.is_dir()]
        else:
            results += [x for x in target.iterdir() if x.is_dir()]

        return [x for x in results if self.filter(x)]




class FileGlobberSingle(FileGlobberMulti):
    """
    Late globber, generates one subtask per root point,
    use self.glob_target to run the glob
    """
    def _build_tasks(self):
        """
        Generalized task builder for globbing on files
        then customizing the subtasks
        """
        subtasks = []
        for n, fpath in enumerate(self.roots):
            subtask = self._build_subtask(n, str(fpath), fpath)
            if subtask is not None:
                subtasks.append(subtask)

        subtasks.append(self._build_setup())
        subtasks.append(self._build_teardown([f"{x['basename']}:{x['name']}" for x in subtasks]))

        top_task = self.default_task()
        top_task.update({"task_dep" : [f"_{self.base}:post"]})
        subtasks.append(self.top_detail(top_task))

        self.total_subtasks = len(subtasks)
        for sub in subtasks:
            if sub is not None:
                yield sub


class RootlessFileGlobber(FileGlobberMulti):
    """
    Glob for files, but don't provide a top level task to
    run all of them together
    """

    def _build_tasks(self):
        """
        Generalized task builder for globbing on files
        then customizing the subtasks
        """
        subtasks = []
        globbed = self.glob_all()
        for i, (uname, fpath) in enumerate(self.glob_all()):
            subtask = self._build_subtask(i, uname, fpath)
            if subtask is not None:
                subtasks.append(subtask)

        subtasks.append(self._build_teardown([f"{x['basename']}:{x['name']}" for x in subtasks]))
        subtasks.append(self._build_setup())

        top_task = self.default_task()
        subtasks.append(self.top_detail(top_task))

        self.total_subtasks = len(subtasks)

        for sub in subtasks:
            if sub is not None:
                yield sub
