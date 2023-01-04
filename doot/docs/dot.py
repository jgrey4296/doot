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

import doot
from doot.files.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
from doot.utils import globber

##-- end imports



class DotVisualise(globber.FileGlobberMulti):
    """
    make images from any dot files
    """

    def __init__(self, dirs:DootLocData, targets, ext="png", layout="neato", scale:float=72.0):
        super().__init__("dot::visual", dirs, targets, [".dot"])
        self.ext       = ext
        self.layout    = layout
        self.scale     = scale


    def subtask_detail(self, fpath, task):
        task.update({
                     "file_dep" : [ fpath ],
                     "targets"  : [ self.dirs.build / fpath.with_suffix(f".{self.ext}").name ],
                     "clean"    : True,
        })
        return task

    def subtask_actions(self, fpath):
        return [ CmdAction(self.run_on_target, shell=False) ]

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
