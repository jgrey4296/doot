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
from doot.mixins.plantuml import PlantUMLMixin
from doot.mixins.dot import DotMixin
from doot import globber, tasker


class DotVisualise(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, DotMixin):
    """
    ([src] -> build) make images from any dot files
    https://graphviz.org/doc/info/command.html
    """

    def __init__(self, name=f"dot::visual", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], exts=[".dot"], rec=rec)
        self.output = self.locs.build

    def set_params(self):
        return self.target_params() + self.dot_params()

    def subtask_detail(self, task, fpath=None):
        dst = self.locs.build / "dot" / fpath.with_suffix(f".{self.args['ext']}").name
        task.update({
            "file_dep" : [ fpath ],
            "targets"  : [ target ],
            "clean"    : True,
            "actions"  : [ self.make_cmd(self.dot_image, fpath, dst) ],
            })
        return task

class PlantUMLGlobberTask(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, CommanderMixin, PlantUMLMixin):
    """
    ([visual] -> build) run plantuml on a specification, generating target.'ext's
    """

    def __init__(self, name="plantuml::visual", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], exts=[".plantuml"], rec=True)
        self.locs.ensure("visual", "build", task=name)
        self.output = self.locs.build

    def set_params(self):
        return self.target_params() + self.plantuml_params() + [
            {"name" : "check", "long": "check", "type": bool, "default": False}
            ]

    def subtask_detail(self, task, fpath=None):
        targ_fname = fpath.with_suffix(f".{self.args['ext']}")
        dst = self.locs.build / targ_fname.name
        task.update({
            "targets"  : [ dst ],
            "file_dep" : [ fpath ],
            "clean"    : True,
            "actions"  : [ self.make_cmd(self.dot_plantuml, fpath, dst, self.args['check']) ],
        })
        return task
