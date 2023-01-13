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
from doot.utils import globber
from doot.utils.tasker import DootTasker

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

class LatexCheckSweep(globber.EagerFileGlobber):
    """
    ([src] -> temp) Run a latex pass, but don't produce anything,
    just check the syntax
    """

    def __init__(self, name="tex::check", dirs:DootLocData=None, roots:list[pl.Path]=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], exts=['.tex'], rec=rec)

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
                     })
        task['actions'] += self.subtask_actions(fpath)

        return task

    def subtask_actions(self, fpath):
        return [ CmdAction((self.build_draft_cmd, [fpath], {}), shell=False) ]

    def build_draft_cmd(self, fpath, interaction):
        no_suffix = fpath.with_suffix("")
        return ["pdflatex", "-draftmode", f"-interaction={interaction}", f"-output-directory={self.dirs.temp}", no_suffix]

class BibtexCheckSweep(globber.EagerFileGlobber):
    """
    TODO ([src])
    """

    def __init__(self, name="bibtex::check", dirs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], exts=['.bib'], rec=rec)

    def subtask_detail(self, task, fpath=None):
        task.update({})
        return task


