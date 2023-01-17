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

import doot
from doot import globber
from doot import tasker

##-- end imports

class DotVisualise(globber.EagerFileGlobber, tasker.DootActions):
    """
    ([src] -> build) make images from any dot files
    """

    def __init__(self, name=None, dirs:DootLocData=None, roots=None, ext="png", layout="neato", scale:float=72.0, rec=True):
        name = name or f"dot::{ext}"
        super().__init__(name, dirs, roots or [dirs.src], exts=[".dot"], rec=rec)
        self.ext       = ext
        self.layout    = layout
        self.scale     = scale

    def subtask_detail(self, task, fpath=None):
        task.update({
            "file_dep" : [ fpath ],
            "targets"  : [ self.dirs.build / fpath.with_suffix(f".{self.ext}").name ],
            "clean"    : True,
            "actions' : "[ self.cmd(self.run_on_target) ],
            })
        return task

    def run_on_target(self, dependencies, targets):
        cmd = ["dot"]
        # Options:
        cmd +=[f"-T{self.ext}", f"-K{self.layout}", f"-s{self.scale}"]
        # file to process:
        cmd.append(dependencies[0])
        # output to:
        cmd += ["-o", targets[0]]
        return cmd

class MakeGraph:
    """ use graphviz's gvgen to generate graphs """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        return {}
