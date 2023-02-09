#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

from typing import Final
import pathlib as pl
import shutil
from functools import partial
from itertools import cycle, chain

import doot
from doot import tasker
from doot import globber

##-- end imports

src_ext      : Final = doot.config.on_fail(".lp", str).tool.doot.clingo.src_ext()
out_ext      : Final = doot.config.on_fail(".lp_result", str).tool.doot.clingo.out_ext()

vis_src_ext  : Final = doot.config.on_fail(".lp_vis", str).tool.doot.clingo.vis_src_ext()
vis_in_ext   : Final = doot.config.on_fail(".json", str).tool.doot.clingo.vis_in_ext()
vis_out_ext  : Final = doot.config.on_fail(".dot", str).tool.doot.clingo.vis_out_ext()

clingo_call  : Final = ["clingo"] + data.toml.on_fail([], list).tool.doot.clingo.options()

class TODOClingoCheck:
    """
    check a file can be parsed by clingo
    """
    pass

class ClingoRunner(globber.DootEagerGlobber, ActionsMixin):
    """
    ([src] -> build) Run clingo on ansprolog sources
    """

    def __init__(self, name="clingo::run", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], exts=[src_ext], rec=rec)
        self.locs.ensure("build")

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
        super().__init__(name, locs, roots or [locs.src], exts=[vis_src_ext], rec=rec)
        self.locs.ensure("build")

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


class TODOClingoVisualise(globber.DootEagerGlobber, ActionsMixin):
    """
    ([src] -> visual) Take clingo output with nodes,
    and convert to dot format
    """

    def __init__(self, name="clingo::visual", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], exts=[vis_in_ext], rec=rec)
        self.locs.ensure("visual")

    def subtask_detail(self, task, fpath=None):
        target = self.locs.visual / targ_fname
        task.update({
            "targets"  : [ target ],
            "task_dep" : [ "_checkdir::clingo" ],
            "actions"  : [],
        })
        return task
