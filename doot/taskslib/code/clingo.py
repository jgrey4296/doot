#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil
from functools import partial
from itertools import cycle, chain

import doot
from doot import tasker
from doot import globber

##-- end imports

src_ext     = doot.config.or_get(".lp", str).tool.doot.clingo.src_ext()
out_ext     = doot.config.or_get(".lp_result", str).tool.doot.clingo.out_ext()

vis_src_ext = doot.config.or_get(".lp_vis", str).tool.doot.clingo.vis_src_ext()
vis_in_ext  = doot.config.or_get(".json", str).tool.doot.clingo.vis_in_ext()
vis_out_ext = doot.config.or_get(".dot", str).tool.doot.clingo.vis_out_ext()

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

class ClingoRunner(globber.EagerFileGlobber, ActionsMixin):
    """
    ([src] -> build) Run clingo on ansprolog sources
    """
    gen_toml = gen_toml

    def __init__(self, name="clingo::run", dirs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], exts=[src_ext], rec=rec)

    def subtask_detail(self, task, fpath=None):
        target = self.dirs.build / path.with_suffix(out_ext).name
        task.update({
            "file_dep" : [ fpath ],
            "targets"  : [ target ],
            "actions"  :[ self.cmd(self.clingo_call, save="result"),
                          (self.write_to, [target, "result"])
                         ]
        })
        return task

    def clingo_call(self, task, dependencies):
        return clingo_call + dependencies

class ClingoDotter(globber.EagerFileGlobber, ActionsMixin):
    """
    ([src] -> build) Run specified clingo files to output json able to be visualised
    """
    gen_toml = gen_toml

    def __init__(self, name="clingo::dotter", dirs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], exts=[vis_src_ext], rec=rec)

    def subtask_detail(self, task, fpath=None):
        target = self.dirs.build / path.with_suffix(vis_in_ext).name
        task.update({
            "targets"  : [ target ],
            "file_dep" : [ fpath ],
            "actions" : [self.cmd(self.json_call, save="result"),
                         (self.write_to, [target, "result"])]
            })
        return task

    def json_call(self, task, dependencies):
        return ["clingo", "--outf2"] + dependencies


class ClingoVisualise(globber.EagerFileGlobber, ActionsMixin):
    """
    TODO ([src] -> visual) Take clingo output with nodes,
    and convert to dot format
    """
    gen_toml = gen_toml

    def __init__(self, name="clingo::visual", dirs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], exts=[vis_in_ext], rec=rec)
        assert('visual' in dirs.extra)

    def subtask_detail(self, task, fpath=None):
        target = self.dirs.extra['visual'] / targ_fname
        task.update({
            "targets"  : [ target ],
            "task_dep" : [ "_checkdir::clingo" ],
            "actions"  : [],
        })
        return task
