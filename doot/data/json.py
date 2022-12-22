#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from functools import partial
from itertools import cycle, chain
from doit.action import CmdAction
from doot import build_dir, data_toml, src_dir, gen_dir
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd

##-- end imports

data_dirs = [pl.Path(x) for x in data_toml.tool.doot.json.data_dirs if pl.Path(x).exists()]
rec_dirs  = [pl.Path(x) for x in data_toml.tool.doot.json.recursive_dirs if pl.Path(x).exists()]

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

class JsonSchemaTask:

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        pass

class JsonPythonSchema:
    def __init__(self):
        self.create_doit_tasks = self.build
        self.cmd = "xsdata"

    def get_args(self, task):
        args = ["generate",
                ("--recursive" if task.meta['recursive'] else ""),
                "-p", task.meta['package'], # generate package name
                "--relative-imports", "--postponed-annotations",
                "--kw-only",
                "--frozen",
                "--no-unnest-classes",
                str(task.meta['focus']) ]

        return args

    def generate_on_target(self, task):
        return f"{self.cmd} " + " ".join(self.get_args(task))

    def move_package(self, task):
        package = pl.Path(task.meta['package'])
        package.rename(json_gen_dir / package)

    def build(self):
        for targ, rec in chain(zip(data_dirs, cycle([False])),
                               zip(rec_dirs, cycle([True]))):
            targ_fname = ("rec_" if rec else "") + "_".join(targ.parts[-2:])
            yield {
                "basename" : "json::schema.python",
                "name"     : targ_fname,
                "actions"  : [ CmdAction(self.generate_on_target), self.move_package ],
                "targets"  : [ json_gen_dir / targ_fname ],
                "task_dep" : [ "_xsdata::config", "_checkdir::xml" ],
                "meta"     : { "package"   : targ_fname,
                               "focus"     : targ,
                               "recursive" : rec,
                            }
            }

    def gen_toml(self):
        return """
##-- doot.json
[tool.doot.json]
data_dirs      = []
recursive_dirs = ["pack/__data/core/json"]
##-- end doot.json
"""


class JsonVisualise:

    def __init__(self):
        self.create_doit_tasks = self.build

    def generate_on_target(self, task):
        if task.meta['recursive']:
            globbed = pl.Path(task.meta['focus']).glob("*.xml")
        elif task.meta['focus'].is_dir():
            globbed = pl.Path(task.meta['focus']).rglob("*.xml")
        else:
            globbed = [task.meta['focus']]

        header = f'echo -e "@startjson\n" > {task.targets}'
        footer = f'echo -e "@endjson\n" >> {task.targets}'
        cmd    = f"cat {globbed} >> {task.targets}"
        # cmd2 = "awk 'BEGIN {print \"@startjson\"} END {print \"@endjson\"} {print $0}'"

        return f"{header}; {cmd}; {footer}"

    def build(self):
        for targ, rec in chain(zip(data_dirs, cycle([False])),
                               zip(rec_dirs, cycle([True]))):
            targ_fname = ("rec_" if rec else "") + "_".join(targ.with_suffix(".plantuml").parts[-2:])
            yield {
                "basename" : "json::schema.visual",
                "name"     : pl.Path(targ_fname).stem,
                "actions"  : [ CmdAction(self.generate_on_target) ],
                "targets"  : [ visual_dir / targ_fname ],
                "task_dep" : [ "_checkdir::json" ],
                "meta"     : { "package"   : targ_fname,
                               "focus"     : targ,
                               "recursive" : rec,
                            }
            }
