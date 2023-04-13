#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

import doot
from doot import globber
from doot.tasker import DootTasker

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.latex import LatexMixin


def task_latex_docs():
    """ run texdoc  """
    return {
        "basename" : "tex::docs",
        "actions" : ["texdoc {package}"],
        "params" : [ { "name" : "package", "long" : "package", "short" : "p", "type" : str, "default" : "--help",}],
    }

class LatexCheckSweep(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, LatexMixin):
    """
    ([src] -> temp) Run a latex pass, but don't produce anything,
    just check the syntax
    """

    def __init__(self, name="tex::check", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], exts=['.tex'], rec=rec)
        self.locs.ensure("temp", task=name)

    def set_params(self):
        return self.target_params() + self.latex_params()

    def subtask_detail(self, task, fpath=None):
        task.update({
            "file_dep" : [ fpath ],
            "actions"  : [ self.make_cmd(self.latex_check, fpath) ]
        })
        return task
