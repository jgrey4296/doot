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
from doot import build_dir, data_toml, src_dir, gen_dir
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils import globber

##-- end imports

data_dirs = [pl.Path(x) for x in data_toml.tool.doot.json.data_dirs if pl.Path(x).exists()]

json_gen_dir   = gen_dir
json_build_dir = build_dir / "json"
visual_dir     = json_build_dir   / "visual"

##-- dir checks
json_dir_check = CheckDir(paths=[json_build_dir,
                                 visual_dir,
                                 ],
                          name="json",
                          task_dep=["_checkdir::build"])

##-- end dir checks

class JsonFormatTask(globber.DirGlobber):
    """
    Lint Json files with jq
    """

    def __init__(self, targets=data_dirs, rec=True):
        super().__init__("json::format", [".json"], data_dirs, rec=rec)

    def setup_detail(self, task):
        """
        Add the backup action to setup
        """
        task['actions' ] = [self.backup_jsons]
        return task

    def subtask_detail(self, fpath, task):
        task.update({
            "uptodate" : [False],
            "meta" : { "focus" : fpath }
            })
        return task

    def subtask_actions(self, fpath):
        ext_strs = [f"*{ext}" for ext in self.exts]
        globbed  = {x for ext in ext_strs for x in fpath.rglob(ext)}
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
        globbed  = {x for ext in ext_strs for start in self.starts for x in start.rglob(ext)}

        for btarget in backup_targets:
            backup = btarget.with_suffix(f"{btarget.suffix}.backup")
            if backup.exists():
                continue
            backup.write_text(btarget.read_text())

class JsonPythonSchema(globber.DirGlobber):
    """
    Use XSData to generate python bindings for a directory of json's
    """
    def __init__(self, targets=data_dirs, rec=True):
        super().__init__("json::schema.python", [".json"], targets, rec=rec)

    def subtask_detail(self, fpath, task):
        gen_package = str(json_gen_dir / task['name'])
        task.update({
            "targets"  : [ gen_package ],
            "task_dep" : [ "_xsdata::config", "_checkdir::json" ],
        })
        task["meta"].update({"package" : gen_package})
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction(partial(self.generate_on_target, fpath), shell=False) ]

    def generate_on_target(self, fpath, task):
        args = ["xsdata", "generate",
                ("--recursive" if task.meta['recursive'] else ""),
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

    def __init__(self, targets=data_dirs):
        super().__init__("json::schema.visual", [".json"], targets, rec=True)

    def subtask_detail(self, fpath, task):
        task.update({
            "targets"  : [ visual_dir / task['name'] ],
            "task_dep" : [ "_checkdir::json" ],
        })
        return task

    def subtask_actions(self, fpath):
        return [ partial(self.write_plantuml, fpath) ]

    def write_plantuml(self, fpath, targets):
        header   = "@startjson\n"
        footer   = "\n@endjson\n"
        contents = fpath.read_text()

        with open(pl.Path(targets[0]), 'w') as f:
            f.write(header)
            f.write(contents)
            f.write(footer)
