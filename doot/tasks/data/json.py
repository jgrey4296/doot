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

import doot
from doot import globber, tasker, task_mixins

##-- end imports

class JsonFormatTask(globber.DirGlobMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin):
    """
    ([data] -> data) Lint Json files with jq *inplace*
    """

    def __init__(self, name="json::format.inplace", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".json"], rec=rec)

    def filter(self, fpath):
        if any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        task.update({
            "uptodate" : [False],
            "actions" : [ (self.glob_jsons, [fpath]) ],
            })
        return task

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

class JsonPythonSchema(globber.DirGlobMixin, globber.DootEagerGlobber, task_mixins.ActionsMixin):
    """
    ([data] -> codegen) Use XSData to generate python bindings for a directory of json's
    """

    def __init__(self, name="json::schema.python", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".json"], rec=rec)
        self.locs.ensure("codegen")

    def filter(self, fpath):
        if any(x.suffix in self.exts for x in fpath.iterdir()):
            return self.control.accept
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        gen_package = str(self.locs.codegen / task['name'])
        task.update({
            "targets"  : [ gen_package ],
            "task_dep" : [ "_xsdata::config" ],
            "clean"    : [ (self.rmdirs, [gen_package]) ],
            "actions"  : [ self.cmd(self.generate_on_target, fpath, gen_package) ]
        })
        return task

    def generate_on_target(self, fpath, gen_package, task):
        args = ["xsdata", "generate",
                ("--recursive" if not self.rec else ""),
                "-p", gen_package,
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                fpath
                ]

        return args

class JsonVisualise(globber.DootEagerGlobber, task_mixins.ActionsMixin):
    """
    ([data] -> visual) Wrap json files with plantuml header and footer,
    ready for plantuml to visualise structure
    """

    def __init__(self, name="json::schema.visual", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".json"], rec=rec)
        self.locs.ensure("visual")

    def subtask_detail(self, task, fpath=None):
        task.update({
            "targets"  : [ self.locs.visual / fpath.with_stem(task['name']).name ],
            "actions"  : [ (self.write_plantuml, [fpath]) ]
            })
        return task

    def write_plantuml(self, fpath, targets):
        header   = "@startjson\n"
        footer   = "\n@endjson\n"

        with open(pl.Path(targets[0]), 'w') as f:
            f.write(header)
            f.write(fpath.read_text())
            f.write(footer)
