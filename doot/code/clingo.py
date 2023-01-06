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

improt doot
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils import globber

##-- end imports

src_ext     = doot.config.or_get(".lp").tool.doot.clingo.src_ext()
out_ext     = doot.config.or_get(".lp_result").tool.doot.clingo.out_ext()

vis_src_ext = doot.config.or_get(".lp_vis").tool.doot.clingo.vis_src_ext()
vis_in_ext  = doot.config.or_get(".json").tool.doot.clingo.vis_in_ext()
vis_out_ext = doot.config.or_get(".dot").tool.doot.clingo.vis_out_ext()

clingo_call = ["clingo"] + data.toml.or_get([]).tool.doot.clingo.options()

def gen_toml(self):
    return "\n".join(["[tool.doot.clingo]",
                      "# For running default clingo files:",
                      "src_ext     = \".lp\"",
                      "out_ext     = \".asp_result\"",
                      "options     = []",
                      "# For producing visualisable output:",
                      "vis_src_ext = \".lp_vis\"",
                      "vis_in_ext  = \".json\"",
                      "vis_out_ext = \".dot\"",
                      ])

class ClingoRunner(globber.EagerFileGlobber):
    """
    ([src] -> build) Run clingo on ansprolog sources
    """
    gen_toml = gen_toml

    def __init__(self, dirs:DootLocData, roots=None):
        super().__init__("clingo::run", dirs, roots or [dirs.src], exts=[src_ext], rec=True)

    def subtask_detail(self, fpath, task):
        target = self.dirs.build / path.with_suffix(out_ext).name
        task.update({
            "file_dep" : [ fpath ],
            "targets"  : [ target ],
        })
        return task

    def subtask_actions(self, fpath):
        return [CmdAction(self.clingo_call, shell=False, save_out="result"),
                self.save_result ]

    def clingo_call(self, task, dependencies):
        return clingo_call + dependencies

    def save_result(self, task, targets):
        result = task.values['result']
        pl.Path(targets[0]).write_text(result)


class ClingoDotter(globber.EagerFileGlobber):
    """
    ([src] -> build) Run specified clingo files to output json able to be visualised
    """
    gen_toml = gen_toml

    def __init__(self, dirs:DootLocData, roots=None):
        super().__init__("clingo::dotter", dirs, roots or [dirs.src], exts=[vis_src_ext], rec=True)

    def subtask_detail(self, fpath, task):
        target = self.dirs.build / path.with_suffix(vis_in_ext).name
        task.update({
            "targets"  : [ target ],
            "file_dep" : [ fpath ],
        })
        return task


    def subtask_actions(self, fpath):
        return [CmdAction(self.json_call, shell=False, save_out="result"),
                self.save_result ]

    def json_call(self, task, dependencies):
        return ["clingo", "--outf2"] + dependencies

    def save_result(self, task, targets):
        result = task.values['result']
        pl.Path(targets[0]).write_text(result)




class ClingoVisualise(globber.EagerFileGlobber):
    """
    ([src] -> visual) Take clingo output with nodes,
    and convert to dot format
    """
    gen_toml = gen_toml

    def __init__(self, dirs:DootLocData, roots=None):
        super().__init__("clingo::visual", dirs, roots or [dirs.src], exts=[vis_in_ext])
        assert('visual' in dirs.extra)

    def subtask_detail(self, fpath, task):
        target = self.dirs.extra['visual'] / targ_fname
        task.update({
            "targets"  : [ target ],
            "task_dep" : [ "_checkdir::clingo" ],
        })
        return task


    def subtask_actions(self, fpath):
        # TODO convert json out from clingo to dot
        return []

