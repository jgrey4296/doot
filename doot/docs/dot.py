#!/usr/bin/env python3
"""
https://graphviz.org/doc/info/command.html
"""
##-- imports
from __future__ import annotations

import pathlib as pl
import shutil

from functools import partial
from itertools import cycle, chain
from doit.action import CmdAction
from doot import build_dir, data_toml, src_dir
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils.general import build_cmd
from doot.utils import globber

##-- end imports

dot_build_dir = build_dir / "dot"
visual_dir    = dot_build_dir   / "visual"

##-- dir checks
dot_dir_check = CheckDir(paths=[dot_build_dir,
                                visual_dir,
                                ],
                         name="dot",
                         task_dep=["_checkdir::build"])

##-- end dir checks

class DotVisualise(globber.FileGlobberMulti):
    """
    make images from any dot files
    """

    def __init__(self):
        super().__init__("dot::visual", [".dot"], [dot_build_dir])

    def generate_on_target(self):
        cmd     = "dot -T{ext} -K{layout} -s{scale} {dependencies} -o {targets}.{ext}"
        return cmd

    def subtask_detail(self, fpath, task):
        task.update({"actions"  : [ CmdAction(self.generate_on_target) ],
                     "file_dep" : [ fpath ],
                     "targets"  : [ visual_dir / fpath.with_suffix(".png").name ],
                     "task_dep" : [ "_checkdir::dot" ],
                     "clean"    : True,
                     "params"   : [{"name"    : "ext", "short"   : "e", "type"    : str, "default" : "png",},
                                   {"name"    : "layout", "short"   : "l", "type"    : str, "default" : "neato",},
                                   {"name"    : "scale", "short"   : "s", "type"    : float, "default" : 72.0,},
                                   ],
                     })
        return task



class MakeGraph:
    """ use graphviz's gvgen to generate graphs """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        return {}
