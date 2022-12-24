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

input_ext  = data_toml.or_get(".lp").tool.doot.clingo.src_ext
output_ext = data_toml.or_get(".asp_result").tool.doot.clingo.out_ext
clingo_opts = data.toml.or_get([]).tool.doot.clingo.options

clingo_gen_dir   = gen_dir
clingo_build_dir = build_dir / "clingo"
visual_dir       = clingo_build_dir   / "visual"

##-- dir checks
clingo_dir_check = CheckDir(paths=[clingo_build_dir,
                                   visual_dir,
                                   ],
                            name="clingo",
                            task_dep=["_checkdir::build"])

##-- end dir checks

# TODO make globber
class ClingoRun:
    """
    Run clingo on ansprolog sources
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        for path in src_dir.rglob(f"*{input_ext}"):
            return {
                "basename" : "clingo::run",
                "name"     : path.stem,
                "actions"  : [f"clingo {clingo_options} " + "{dependencies} > {targets}"],
                "file_dep" : [path],
                "targets"  : [ clingo_build_dir / path.with_suffix(output_ext).name ],
            }

    def gen_toml(self):
        return "\n".join(["##-- clingo",
                          "[tool.doot.clingo]",
                          "src_ext = \".lp\"",
                          "out_ext = \".asp_result\"",
                          "options = []",
                          "##-- end clingo"])

class ClingoVisualise:
    """
    Take clingo output with nodes,
    and convert to dot format
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def generate_on_target(self, task):
        if task.meta['recursive']:
            globbed = pl.Path(task.meta['focus']).glob("*.xml")
        elif task.meta['focus'].is_dir():
            globbed = pl.Path(task.meta['focus']).rglob("*.xml")
        else:
            globbed = [task.meta['focus']]

        return f"{header}; {cmd}; {footer}"

    def build(self):
        for targ, rec in chain(zip(data_dirs, cycle([False])),
                               zip(rec_dirs, cycle([True]))):
            targ_fname = ("rec_" if rec else "") + "_".join(targ.with_suffix(".plantuml").parts[-2:])
            yield {
                "basename" : "clingo::visual",
                "name"     : pl.Path(targ_fname).stem,
                "actions"  : [ CmdAction(self.generate_on_target) ],
                "targets"  : [ visual_dir / targ_fname ],
                "task_dep" : [ "_checkdir::clingo" ],
                "meta"     : { "package"   : targ_fname,
                               "focus"     : targ,
                               "recursive" : rec,
                            }
            }
