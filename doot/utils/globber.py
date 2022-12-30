#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
import shutil

from doit.action import CmdAction
from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


class FileGlobberMulti:
    """
    Base task for file based *on load* globbing.
    Generates a new subtask for each file found.

    Each File found is a separate subtask

    """

    def __init__(self, base:str, exts:list[str], starts:list[pl.Path], rec=False,
                 defaults:None|dict=None, filter_fn:callable=None):
        self.create_doit_tasks    = self.build
        self.base                 = base
        self.exts                 = exts[:]
        self.starts               = starts[:]
        self.rec                  = rec
        self.filter_fn            = filter_fn
        self.defaults             = defaults or {}
        self.total_subtasks       = 0

        try:
            split_doc = [x for x in self.__class__.__doc__.split("\n") if bool(x)]
            self.doc               = split_doc[0] if bool(split_doc) else ""
        except AttributeError:
            self.doc = ":: default"

    def glob_target(self, target, rec=False):
        results = []
        if rec or self.rec:
            for ext in self.exts:
                results += list(target.rglob("*"+ext))
        else:
            for ext in self.exts:
                results += list(target.glob("*"+ext))

        if self.filter_fn is not None:
            results = [x for x in results if self.filter_fn(x)]

        return results

    def glob_all(self, rec=False) -> list[tuple(pl.Path, str)]:
        """
        Glob all available files,
        and generate unique names for them
        """
        globbed = set()
        for start in self.starts:
            globbed.update(self.glob_target(start, rec=rec))

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

    def subtask_detail(self, fpath:pl.Path, task:dict) -> dict:
        """
        override to add any additional task details
        """
        return task

    def setup_detail(self, task:dict) -> dict:
        return task
    def teardown_detail(self, task:dict) -> dict:
        return task

    def top_detail(self, task:dict) -> dict:
        return task
    def default_task(self) -> dict:
        return self.defaults.copy()


    def _build_setup(self) -> dict:
        """
        Build a pre-task that every subtask depends on
        """
        task_spec = {"basename" : f"_{self.base}:pretask",
                     "actions"  : [],
                     }
        task_spec = self.setup_detail(task_spec)
        return task_spec

    def _build_subtask(self, n, uname, fpath):
        spec_doc  = self.doc.strip() + f" : {fpath}"
        task_spec = self.default_task()
        task_spec['meta'] = { "n" : n }
        task_spec["task_dep"] = [f"_{self.base}:pretask"]

        task_spec.update({"basename" : self.base,
                          "name"     : uname,
                          "actions"  : [],
                          "doc"      : spec_doc,
                          })
        task = self.subtask_detail(fpath, task_spec)
        task['actions'] += self.subtask_actions(fpath)

        return task
    def _build_teardown(self, subnames:list[str]) -> dict:
        task_spec = {
            "basename" : f"_{self.base}",
            "name"     : "post",
            "task_dep" : subnames,
            "actions"  : [],
            "doc"      : "Post Action",
        }
        task = self.teardown_detail(task_spec)
        return task


    def build(self):
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

        subtasks.append(self._build_teardown([f"{self.base}:{x['name']}" for x in subtasks]))
        subtasks.append(self._build_setup())

        top_task = {
            "basename" : f"{self.base}",
            "name"     : None,
            "task_dep" : [f"_{self.base}:post"],
            "doc"      : self.doc,
        }
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

        if self.filter_fn is not None:
            return [x for x in results if self.filter_fn(x)]
        else:
            return results




class FileGlobberLate(FileGlobberMulti):
    """
    Late globber, generates one subtask per start point,
    use self.glob_target to run the glob
    """
    def build(self):
        """
        Generalized task builder for globbing on files
        then customizing the subtasks
        """
        subtasks = []
        for n, fpath in enumerate(self.starts):
            subtask = self._build_subtask(n, str(fpath), fpath)
            if subtask is not None:
                subtasks.append(subtask)

        subtasks.append(self._build_teardown([f"{self.base}:{x['name']}" for x in subtasks]))
        subtasks.append(self._build_setup())

        top_task = { "basename" : f"{self.base}",
                     "name"     : None,
                     "task_dep" : [f"_{self.base}:post"],
                     "doc"      : self.doc,
                    }
        subtasks.append(self.top_detail(top_task))

        self.total_subtasks = len(subtasks)
        for sub in subtasks:
            if sub is not None:
                yield sub


class FileGlobberSingle(FileGlobberMulti):
    """
    Glob for files, but don't provide a top level task to
    run all of them together
    """

    def build(self):
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

        subtasks.append(self._build_teardown([f"{self.base}:{x['name']}" for x in subtasks]))
        subtasks.append(self._build_setup())

        top_task = {
            "basename" : f"{self.base}",
            "name"     : None,
            "doc"      : self.doc,
        }
        subtasks.append(self.top_detail(top_task))

        self.total_subtasks = len(subtasks)

        for sub in subtasks:
            if sub is not None:
                yield sub
