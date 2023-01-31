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


class GodotCheckTask(globber.DootEagerGlobber, ActionsMixin):
    """
    ([root]) Lint all gd scripts in the project
    """
    def __init__(self, name="godot::check", locs:DootLocData=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.root], exts=[".gd"], rec=rec)
        self.failures = set()
        assert(self.locs.build)

    def setup_detail(self, task):
        task.update({
            "actions"  : [self.reset_failures],
            "teardown" : [self.report_failures],
            "target"   : [self.locs.build / "check_fails.report"]
        })
        return task


    def subtask_detail(self, task, fpath=None):
        task.update({"actions"   : [
            self.force(self.build_check,
                       handler=partial(self.handle_failure, fpath)),
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

    def report_failures(self, targets):
        if not bool(self.failures):
            return

        report = ["==========",
                  "Failures Reported In:"]
        report += [f"- {fail}" for fail in self.failures]
        report += ["=========="]
        print("\n".join(report))
        self.write_to(targets[0], report)
        return False

    def reset_failures(self):
        self.failures = set()
