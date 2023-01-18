#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations
from doit.tools import PythonInteractiveAction, Interactive

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

prolog_ext = doot.config.or_get(".pl", str).doot.tool.repls.prolog.ext

def task_pyrepl():
    return {
        "basename" : "repl::py",
        "actions"  : [ PythonInteractiveAction(lambda: breakpoint()) ],
    }

def task_prolog_repl():
    return {
        "basename" : "repl::pl",
        "actions"  : [ Interactive(["swipl"], shell=False)],
    }


class PrologRunner(globber.DootEagerGlobber):
    """
    reminder, to run a goal without printing anything:
    return status is success or fail
    swipl -g "paired(bob,london)" -t halt ./simple.pl
    """

    def __init__(self, name="prolog::query", dirs=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], exts=[prolog_ext], rec=rect)

    def filter(self, fpath):
        # test for it being a main file
        return True

    def subtask_detail(self, task, fpath=None):
        return task
