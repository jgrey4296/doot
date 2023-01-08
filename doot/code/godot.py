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
from doot.utils.general import ForceCmd, regain_focus
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


class GodotCheckTask(globber.EagerFileGlobber):
    """
    ([root]) Lint all gd scripts in the project
    """
    def __init__(self, name="godot::check", dirs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.root], exts=[".gd"], rec=rec)
        self.failures = set()

    def setup_detail(self, task):
        task.update({
            "actions"  : [self.reset_failures],
            "teardown" : [self.report_failures]
        })
        return task


    def subtask_detail(self, fpath, task):
        task.update({"actions"   : [
            ForceCmd(self.build_check, shell=False, handler=partial(self.handle_failure, fpath)),
        ],
                     "file_dep"  : [ fpath ],
                     "uptodate" : [False],
                     })
        return task

    def build_check(self, dependencies):
        return ["godot", "--no-window", "--check-only", "--script", *dependencies]

    def handle_failure(self, fpath, result):
        print("Errors Found in: ", fpath)
        self.failures.add(fpath)
        return None

    def report_failures(self):
        if not bool(self.failures):
            return

        print("==========")
        print("Failures Reported In:")
        for fail in self.failures:
            print("- ", fail)
        print("==========")
        return False

    def reset_failures(self):
        self.failures = set()
