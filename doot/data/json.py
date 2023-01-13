#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from functools import partial
import shlex

from functools import partial
from itertools import cycle, chain
from doit.action import CmdAction

import doot
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils import globber
from doot.utils.clean_dirs import clean_target_dirs

##-- end imports

class JsonFormatTask(globber.DirGlobber):
    """
    ([data] -> data)Lint Json files with jq
    """

    def __init__(self, name="json::format", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".json"], rec=rec)

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.control.accept
        return self.control.discard


    def subtask_detail(self, task, fpath=None):
        task.update({
            "uptodate" : [False],
            })
        task['actions'] += self.subtask_actions(fpath)
        return task

    def subtask_actions(self, fpath):
        return [ (self.glob_jsons, [fpath]) ]

    def glob_jsons(self, fpath):
        globbed  = self.glob_files(fpath)
        self.backup_jsons(globbed)
        for target in globbed:
            # Format
            cmd = CmdAction(["jq", "-M", "-S" , ".", target ], shell=False)
            # and save
            target.write_text(cmd.out)

    def backup_jsons(self, fpaths:list[pl.Path]):
        """
        Find all applicable files, and copy them
        """
        for btarget in fpaths:
            backup = btarget.with_suffix(f"{btarget.suffix}.backup")
            if backup.exists():
                continue
            backup.write_text(btarget.read_text())

class JsonPythonSchema(globber.DirGlobber):
    """
    ([data] -> codegen) Use XSData to generate python bindings for a directory of json's
    """

    def __init__(self, name="json::schema.python", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".json"], rec=rec)

    def filter(self, fpath):
        if any(x.suffix in self.exts for fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        gen_package = str(self.dirs.codegen / task['name'])
        task.update({
            "targets"  : [ gen_package ],
            "task_dep" : [ "_xsdata::config" ],
            "clean"    : [ clean_target_dirs ],
        })
        task["meta"].update({"package" : gen_package})
        task['actions'] += self.subtask_actions(fpath)
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction((self.generate_on_target, [fpath], {}), shell=False) ]

    def generate_on_target(self, fpath, task):
        args = ["xsdata", "generate",
                ("--recursive" if not self.rec else ""),
                "-p", task.meta['package'], # generate package name
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                fpath
                ]

        return args



class JsonVisualise(globber.EagerFileGlobber):
    """
    ([data] -> visual) Wrap json files with plantuml header and footer,
    ready for plantuml to visualise structure
    """

    def __init__(self, name="json::schema.visual", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".json"], rec=rec)
        assert('visual' in dirs.extra)


    def subtask_detail(self, task, fpath=None):
        task.update({
            "targets"  : [ self.dirs.extra['visual'] / fpath.with_stem(task['name']).name ],
        })
        task['actions'] += self.subtask_actions(fpath)
        return task

    def subtask_actions(self, fpath):
        return [ (self.write_plantuml, [fpath]) ]

    def write_plantuml(self, fpath, targets):
        header   = "@startjson\n"
        footer   = "\n@endjson\n"

        with open(pl.Path(targets[0]), 'w') as f:
            f.write(header)
            f.write(fpath.read_text())
            f.write(footer)
