#!/usr/bin/env python3
"""

"""
##-- imports

##-- end imports

##-- default imports
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

##-- end default imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class DotVisualise(globber.DootEagerGlobber, tasker.ActionsMixin):
    """
    ([src] -> build) make images from any dot files
    https://graphviz.org/doc/info/command.html
    """

    def __init__(self, name=None, locs:DootLocData=None, roots=None, ext="png", layout="neato", scale:float=72.0, rec=True):
        name = name or f"dot::{ext}"
        super().__init__(name, dirs, roots or [dirs.src], exts=[".dot"], rec=rec)
        self.ext       = ext
        self.layout    = layout
        self.scale     = scale

    def subtask_detail(self, task, fpath=None):
        task.update({
            "file_dep" : [ fpath ],
            "targets"  : [ self.locs.build / fpath.with_suffix(f".{self.ext}").name ],
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

class DotMakeGraph:
    """
    TODO use graphviz's gvgen to generate graphs
    https://graphviz.org/doc/info/command.html
    """

    def __init__(self):
        self.create_doit_tasks = self.build

    def build(self):
        return {}

class PlantUMLGlobberTask(globber.DootEagerGlobber, tasker.ActionsMixin):
    """
    ([visual] -> build) run plantuml on a specification, generating target.'ext's
    """

    def __init__(self, name=None, locs:DootLocData=None, roots:list[pl.Path]=None, fmt="png", rec=True):
        assert(roots or 'visual' in dirs.extra)
        name = name or f"plantuml::{fmt}"
        super().__init__(name, dirs, roots or [dirs.src], exts=[".plantuml"], rec=True)
        self.fmt       = fmt

    def subtask_detail(self, task, fpath=None):
        targ_fname = fpath.with_suffix(f".{self.fmt}")
        task.update({"targets"  : [ self.locs.build / targ_fname.name],
                     "file_dep" : [ fpath ],
                     "task_dep" : [ f"plantuml::check:{task['name']}" ],
                     "clean"     : True,
                     "actions" : [ self.cmd(self.run_plantuml) ],
                     })
        return task

    def run_plantuml(self, dependencies, targets):
        return ["plantuml", f"-t{self.fmt}",
                "-output", self.locs.build.resolve(),
                "-filename", targets[0],
                dependencies[0]
                ]

class PlantUMLGlobberCheck(globber.DootEagerGlobber, tasker.ActionsMixin):
    """
    ([visual]) check syntax of plantuml files
    TODO Adapt godot::check pattern
    """

    def __init__(self, name="plantuml::check", locs=None, roots:list[pl.Path]=None, rec=True):
        assert(roots or 'visual' in dirs.extra)
        super().__init__(name, dirs, roots or [dirs.extra['visual']], exts=[".plantuml"], rec=rec)

    def subtask_detail(self, task, fpath=None):
        task.update({
            "file_dep" : [ fpath ],
            "uptodate" : [ False ],
            "actions"  : [ self.cmd(self.check_action) ],
            })
        return task

    def check_action(self, dependencies):
        return ["plantuml", "-checkonly", *dependencies]
