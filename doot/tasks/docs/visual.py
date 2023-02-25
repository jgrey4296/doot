#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doot.mixins.filer import FilerMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot import globber, tasker

dot_scale  = doot.config.on_fail(72.0, float).tool.doot.dot_graph.scale()
dot_layout = doot.config.on_fail("neato", str).tool.doot.dot_graph.layout()
dot_ext    = doot.config.on_fail("png", str).tool.doot.dot_graph.ext()

plant_ext  = doot.config.on_fail("png", str).tool.doot.plantuml.ext()

class DotVisualise(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin):
    """
    ([src] -> build) make images from any dot files
    https://graphviz.org/doc/info/command.html
    """

    def __init__(self, name=f"dot::visual", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], exts=[".dot"], rec=rec)
        self.output = self.locs.build

    def set_params(self):
        return self.target_params() + [
            { "name" : "layout", "type": str,   "short": "l", "default": dot_layout},
            { "name" : "scale" , "type": float, "short", "s", "default": dot_scale},
            { "name" : "ext",    "type": str,   "short": "e", "default": dot_ext}
        ]

    def subtask_detail(self, task, fpath=None):
        task.update({
            "file_dep" : [ fpath ],
            "targets"  : [ self.locs.build / fpath.with_suffix(f".{self.ext}").name ],
            "clean"    : True,
            "actions"  : [ self.cmd(self.visualise_graph) ],
            })
        return task

    def visualise_graph(self, dependencies, targets):
        cmd = ["dot"]
        # Options:
        cmd +=[f"-T{self.args['ext']}", f"-K{self.args['layout']}", f"-s{self.args['scale']}"]
        # file to process:
        cmd.append(dependencies[0])
        # output to:
        cmd += ["-o", targets[0]]
        return cmd

class PlantUMLGlobberTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin):
    """
    ([visual] -> build) run plantuml on a specification, generating target.'ext's
    """

    def __init__(self, name="plantuml::visual",, locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], exts=[".plantuml"], rec=True)
        self.locs.ensure("visual", "build")
        self.output = self.locs.build

    def set_params(self):
        return self.target_params() + [
            { "name" : "ext", "type": str, "short": "e", "default": plant_ext},
        ]

    def subtask_detail(self, task, fpath=None):
        targ_fname = fpath.with_suffix(f".{self.args['ext']}")
        target     = self.locs.build / targ_fname.name
        task.update({"targets"  : [ target ],
                     "file_dep" : [ fpath ],
                     "clean"     : True,
                     "actions" : [ self.cmd(self.run_plantuml, target, fpath) ],
                     })
        return task

    def run_plantuml(self, plOut, plIn):
        return ["plantuml", f"-t{self.args['ext']}",
                "-output", self.output.resolve(),
                "-filename", plOut,
                plIn
                ]

class PlantUMLGlobberCheck(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, FilerMixin):
    """
    ([visual]) check syntax of plantuml files
    """

    def __init__(self, name="plantuml::check", locs=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.visual], exts=[".plantuml"], rec=rec)
        self.locs.ensure(roots, 'visual')
        self.output = self.locs.temp / "plantuml"/ "checked.report"

    def set_params(self):
        return self.target_params()

    def task_detail(self, task):
        task.update({
            "targets": [ self.output ],
            "clean"  : True,
        })
        return task

    def subtask_detail(self, task, fpath=None):
        task.update({
            "file_dep" : [ fpath ],
            "uptodate" : [ False ],
            "actions"  : [
                self.cmd("plantuml", "-checkonly", fpath, save="checked"),
                (self.write_to, [self.output, "checked"]),
            ],
        })
        return task

class TODODotMakeGraph(tasker.DootTasker):
    """
    TODO use graphviz's gvgen to generate graphs
    https://graphviz.org/doc/info/command.html
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        return {}
