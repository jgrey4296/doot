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
from doot import data_toml
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils import globber

##-- end imports

class JsonFormatTask(globber.DirGlobber):
    """
    Lint Json files with jq
    """

    def __init__(self, dirs:DootDirs, targets:list[pl.Path], rec=True):
        super().__init__("json::format", dirs, targets, exts=[".json"], rec=rec)

    def setup_detail(self, task):
        """
        Add the backup action to setup
        """
        task['actions' ] = [self.backup_jsons]
        return task

    def subtask_detail(self, fpath, task):
        task.update({
            "uptodate" : [False],
            })
        return task

    def subtask_actions(self, fpath):
        globbed  = {x for ext in self.exts for x in fpath.rglob(f"*{ext}")}
        actions  = []

        for target in globbed:
            args = ["jq", "-M", "-S" , ".", target ]

            # Format and save result:
            actions.append(CmdAction(args, shell=False, save_out=str(target)))
            # Write result to the file:
            actions.append(partial(self.write_formatting, target))

        return actions


    def write_formatting(self, target, task):
        formatted_text = task.values[str(target)]
        target.write_text(formatted_text)

    def backup_jsons(self):
        """
        Find all applicable files, and copy them
        """
        ext_strs = [f"*{ext}" for ext in self.exts]
        globbed  = {x for ext in ext_strs for root in self.roots for x in root.rglob(ext)}

        for btarget in backup_targets:
            backup = btarget.with_suffix(f"{btarget.suffix}.backup")
            if backup.exists():
                continue
            backup.write_text(btarget.read_text())

class JsonPythonSchema(globber.DirGlobber):
    """
    Use XSData to generate python bindings for a directory of json's
    """
    def __init__(self, dirs:DootDirs, targets:list[pl.Path], rec=True):
        super().__init__("json::schema.python", dirs, targets, exts=[".json"], rec=rec)

    def subtask_detail(self, fpath, task):
        gen_package = str(self.dirs.codegen / task['name'])
        task.update({
            "targets"  : [ gen_package ],
            "task_dep" : [ "_xsdata::config"],
        })
        task["meta"].update({"package" : gen_package})
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction(partial(self.generate_on_target, fpath), shell=False) ]

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

    def gen_toml(self):
        return """
##-- doot.json
[tool.doot.json]
data_dirs      = []
recursive_dirs = ["pack/__data/core/json"]
##-- end doot.json
"""


class JsonVisualise(globber.FileGlobberMulti):
    """
    Wrap json files with plantuml header and footer,
    ready for plantuml to visualise structure
    """

    def __init__(self, dirs:DootDirs, targets:list[pl.Path]):
        super().__init__("json::schema.visual", dirs, targets, exts=[".json"], rec=True)

    def subtask_detail(self, fpath, task):
        task.update({
            "targets"  : [ self.dirs.visual / fpath.with_stem(task['name']).name ],
        })
        return task

    def subtask_actions(self, fpath):
        return [ partial(self.write_plantuml, fpath) ]

    def write_plantuml(self, fpath, targets):
        header   = "@startjson\n"
        footer   = "\n@endjson\n"

        with open(pl.Path(targets[0]), 'w') as f:
            f.write(header)
            f.write(fpath.read_text())
            f.write(footer)
