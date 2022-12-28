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
from doot.utils import globber

##-- end imports

src_ext     = data_toml.or_get(".lp").tool.doot.clingo.src_ext()
out_ext     = data_toml.or_get(".lp_result").tool.doot.clingo.out_ext()

vis_src_ext = data_toml.or_get(".lp_vis").tool.doot.clingo.vis_src_ext()
vis_in_ext  = data_toml.or_get(".json").tool.doot.clingo.vis_in_ext()
vis_out_ext = data_toml.or_get(".dot").tool.doot.clingo.vis_out_ext()

clingo_opts = " ".join(data.toml.or_get([]).tool.doot.clingo.options())

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

class ClingoRunner(globber.FileGlobberMulti):
    """
    Run clingo on ansprolog sources
    """

    def __init__(self):
        super().__init__("clingo::run", [src_ext], [src_dir], rec=True)

    def subtask_actions(self, fpath):
        return [CmdAction(f"clingo {clingo_options} " + "{dependencies} > {targets}")]

    def subtask_detail(self, fpath, task):
        target = clingo_build_dir / path.with_suffix(out_ext).name
        task.update({
            "file_dep" : [fpath],
            "targets"  : [ target ],
            "task_dep" : ["_checkdir::clingo"],
        })
        return task

    def gen_toml(self):
        return "\n".join(["##-- clingo",
                          "[tool.doot.clingo]",
                          "src_ext = \".lp\"",
                          "out_ext = \".asp_result\"",
                          "options = []",
                          "##-- end clingo"])

class ClingoDotter(globber.FileGlobberMulti):
    """
    Run specified clingo files to output json able to be visualised
    """

    def __init__(self):
        super().__init__("clingo::dotter", [vis_src_ext], [src_dir], rec=True)

    def subtask_actions(self, fpath):
        return [CmdAction(f"clingo --outf=2 {clingo_options} " + "{dependencies} > {targets}")]

    def subtask_detail(self, fpath, task):
        target = clingo_build_dir / path.with_suffix(vis_in_ext).name
        task.update({
            "targets" : [target],
            "file_dep" : [fpath],
        })
        task['meta'].update({

        })
        return task

    def gen_toml(self):
        return "\n".join(["##-- clingo",
                          "[tool.doot.clingo]",
                          "vis_src_ext = \".lp_vis\"",
                          "vis_in_ext = \".json\"",
                          "vis_out_ext = \".dot\"",
                          "options = []",
                          "##-- end clingo"])

class ClingoVisualise(globber.FileGlobberMulti):
    """
    Take clingo output with nodes,
    and convert to dot format
    """

    def __init__(self):
        super().__init__("clingo::visual", [vis_in_ext], [clingo_build_dir])

    def subtask_actions(self, fpath):
        # TODO convert json out from clingo to dot
        return []

    def subtask_detail(self, fpath, task):
        target = visual_dir / targ_fname
        task.update({
            "targets"  : [target],
            "task_dep" : [ "_checkdir::clingo" ],
        })
        task['meta'].update({

        })
        return task

    def gen_toml(self):
        return "\n".join(["##-- clingo",
                          "[tool.doot.clingo]",
                          "vis_src_ext = \".json\"",
                          "vis_out_ext = \".dot\"",
                          "##-- end clingo"])
