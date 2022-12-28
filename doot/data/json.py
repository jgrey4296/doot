#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
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

    def format_jsons(self, task):
        ext_strs    = [f"*{ext}" for ext in self.exts]
        globbed     = {x for ext in ext_strs for x in task.meta['focus'].rglob(ext)}
        format_cmds = []

        for target in globbed:
            target_q   = shlex.quote(str(target))
            new_fmt    = shlex.quote(str(target.with_name(f"{target.name}.format")))
            fmt_backup = shlex.quote(str(target.with_name(f"{target.name}.backup")))

            fmt_cmd = ["jq", "-M", "-S" , "."
                       , target_q , ">" , new_fmt , ";"
                       , "mv" , "--verbose", "--update",  new_fmt, target_q
                       ]
            format_cmds.append(" ".join(fmt_cmd))

        return "; ".join(format_cmds)

    def subtask_actions(self, fpath):
        ext_strs = [f"*{ext}" for ext in self.exts]

        find_names  = " -o ".join(f"-name \"{ext}\"" for ext in ext_strs)
        depth = ""
        if self.rec:
            depth = "-maxdepth 1"

        backup_cmd = f"find {fpath} {depth} {find_names} | xargs -I %s cp --verbose --no-clobber %s %s.backup"
        total_cmds = [ CmdAction(backup_cmd), CmdAction(self.format_jsons) ]
        return total_cmds

    def subtask_detail(self, fpath, task):
        task.update({
            "uptodate" : [False],
            "meta" : { "focus" : fpath }
            })
        return task

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
        for targ, rec in chain(zip(data_dirs, cycle([False]))):
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
        for targ, rec in chain(zip(data_dirs, cycle([False]))):
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
