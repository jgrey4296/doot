#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from doit.action import CmdAction

from doot import build_dir, data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports


class EarlyGlobber:
    """
    Base task for *early* globbing over a bunch of directories
    ie: on load, not on task run

    Each File found is a separate subtask

    """

    def __init__(self, base:str, exts:list[str], starts:list[pl.Path], rec=False):
        self.create_doit_tasks = self.build
        self.base              = base
        self.exts              = exts[:]
        self.starts            = starts[:]
        self.rec               = rec
        split_doc = [x for x in self.__class__.__doc__.split("\n") if bool(x)]
        self.doc               = split_doc[0] if bool(split_doc) else ""

    def glob_all(self, rec=False) -> list[tuple(pl.Path, str)]:
        """
        Glob all available files,
        and generate unique names for them
        """
        if rec or self.rec:
            # Glob recursively
            globbed = {fpath
                       for path  in self.starts
                       for glob  in self.exts
                       for fpath in path.rglob(f"*{glob}")}
        else:
            # or not
            globbed = {fpath
                       for path  in self.starts
                       for glob  in self.exts
                       for fpath in path.glob(f"*{glob}")}

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

    def get_actions(self, fpath) -> list[str|CmdAction|Callable]:
        return [f"echo {fname}"]

    def task_detail(self, fpath:pl.Path, task:dict) -> dict:
        """
        override to add any additional task details
        """
        return task

    def build(self):
        """
        Generalized task builder for globbing on files
        then customizing the subtasks
        """
        yield {
            "basename" : self.base,
            "name" : None,
            "actions" : [],
            "doc" : self.doc,
        }

        for uname, fpath in self.glob_all():
            spec_doc = self.doc.strip() + f" : {fpath}"
            task = self.task_detail(fpath,
                                   {"basename" : self.base,
                                    "name"     : uname,
                                    "actions"  : self.get_actions(fpath),
                                    "doc"      : spec_doc,
                                    })
            yield task



class DirGlobber(EarlyGlobber):
    """
    Globs for directories

    Recursive: all directories from roots down
    Non-Recursive: immediate subdirectories roots
    Always provides the root directories
    """

    def glob_all(self, rec=False) -> list[tuple(pl.Path, str)]:
        """
        Globs all directories, potentially recursively, instead of files

        gets directories only if recursive
        """
        if rec or self.rec:
            # Glob recursively
            globbed = {root for root in self.starts if root.is_dir()}
            queue = self.starts[:]
            while bool(queue):
                current = queue.pop()
                if current.is_file():
                    continue
                contents = list(current.iterdir())
                content_exts = {x.suffix for x in contents}
                if not bool(contents):
                    # no contents, ignore
                    continue

                if not bool(self.exts) or any(x in self.exts for x in content_exts):
                    # there are files with correct extensions to process
                    # or no extensions have been specified
                    globbed.add(current)

                # keep trying
                queue += contents
        else:
            # or not, just get immediate subdirs
            roots   = set(self.starts)
            globbed = {sub for root in roots for sub in root.iterdir() if sub.is_dir()}
            globbed.update(roots)


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

    def build(self):
        """
        Generalized task builder for globbing on files
        then customizing the subtasks
        """

        yield {
            "basename" : self.base,
            "name" : None,
            "actions" : [],
            "doc" : self.doc,
        }

        for uname, fpath in self.glob_all():
            spec_doc = self.doc.strip() + f" : {fpath}"
            task = self.task_detail(fpath,
                                   {"basename" : self.base,
                                    "name"     : uname,
                                    "actions"  : self.get_actions(fpath),
                                    "doc"      : spec_doc,
                                    })
            yield task
