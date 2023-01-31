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
from doot.task_mixins import ActionsMixin

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

# TODO bibtex - reports
# TODO bibtex - clean
# TODO bibtex - file check
# TODO bibtex - indexer
# TODO bibtex - timelines
# TODO bibtex - split

def task_latex_docs():
    """ run texdoc  """
    return {
        "basename" : "tex::docs",
        "actions" : ["texdoc {package}"],
        "params" : [ { "name" : "package",
                       "long" : "package",
                       "short" : "p",
                       "type" : str,
                       "default" : "--help",
                       }
                    ],
    }

class LatexCheckSweep(globber.DootEagerGlobber, ActionsMixin):
    """
    ([src] -> temp) Run a latex pass, but don't produce anything,
    just check the syntax
    """

    def __init__(self, name="tex::check", locs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], exts=['.tex'], rec=rec)
        assert(self.locs.temp)

    def set_params(self):
        return [
            { "name"   : "interaction",
              "short"  : "i",
              "type"    : str,
              "choices" : [ ("batchmode", ""), ("nonstopmode", ""), ("scrollmode", ""), ("errorstopmode", ""),],
              "default" : "nonstopmode",
             },
        ]

    def subtask_detail(self, task, fpath=None):
        task.update({"file_dep" : [ fpath ],
                     "actions"  : [ self.cmd(self.build_draft_cmd, fpath) ]
                     })
        return task

    def build_draft_cmd(self, fpath):
        return ["pdflatex",
                "-draftmode",
                f"-interaction={self.args['interaction']}",
                f"-output-directory={self.locs.temp}",
                fpath.with_suffix("")]

class BibtexCheckSweep(globber.DootEagerGlobber, ActionsMixin):
    """
    TODO ([src]) Bibtex Checking
    """

    def __init__(self, name="bibtex::check", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.src], exts=['.bib'], rec=rec)

    def subtask_detail(self, task, fpath=None):
        task.update({})
        return task
