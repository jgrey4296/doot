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

src_ext     = doot.config.on_fail(".lp", str).tool.doot.clingo.src_ext()
out_ext     = doot.config.on_fail(".lp_result", str).tool.doot.clingo.out_ext()

vis_src_ext = doot.config.on_fail(".lp_vis", str).tool.doot.clingo.vis_src_ext()
vis_in_ext  = doot.config.on_fail(".json", str).tool.doot.clingo.vis_in_ext()
vis_out_ext = doot.config.on_fail(".dot", str).tool.doot.clingo.vis_out_ext()

clingo_call = ["clingo"] + data.toml.on_fail([]).tool.doot.clingo.options()

class ClingoCheck:
    """
    TODO clingo check
    """
    pass
class ClingoRunner(globber.DootEagerGlobber, ActionsMixin):
    """
    ([src] -> build) Run clingo on ansprolog sources
    """

    def __init__(self, name="clingo::run", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], exts=[src_ext], rec=rec)

    def subtask_detail(self, task, fpath=None):
        target = self.locs.build / path.with_suffix(out_ext).name
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

class ClingoDotter(globber.DootEagerGlobber, ActionsMixin):
    """
    ([src] -> build) Run specified clingo files to output json able to be visualised
    """

    def __init__(self, name="clingo::dotter", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], exts=[vis_src_ext], rec=rec)

    def subtask_detail(self, task, fpath=None):
        target = self.locs.build / path.with_suffix(vis_in_ext).name
        task.update({
            "targets"  : [ target ],
            "file_dep" : [ fpath ],
            "actions" : [self.cmd(self.json_call, save="result"),
                         (self.write_to, [target, "result"])]
            })
        return task

    def json_call(self, task, dependencies):
        return ["clingo", "--outf2"] + dependencies


class ClingoVisualise(globber.DootEagerGlobber, ActionsMixin):
    """
    TODO ([src] -> visual) Take clingo output with nodes,
    and convert to dot format
    """

    def __init__(self, name="clingo::visual", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], exts=[vis_in_ext], rec=rec)
        assert('visual' in dirs.extra)

    def subtask_detail(self, task, fpath=None):
        target = self.locs.extra['visual'] / targ_fname
        task.update({
            "targets"  : [ target ],
            "task_dep" : [ "_checkdir::clingo" ],
            "actions"  : [],
        })
        return task
