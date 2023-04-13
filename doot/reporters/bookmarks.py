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


class BookmarksReport(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, FilerMixin):
    """
    TODO Generate reports on bookmarks
    """

    def __init__(self, name="bkmk::report", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.bookmarks], rec=rec, exts=exts or [".bookmarks"])
        self.bookmarks = BC.BookmarkCollection()
        self.output = locs.build

    def filter(self, fpath):
        return self.control.accept

    def task_detail(self, task):
        report_target = self.output / "bookmarks.report"
        task.update({
            "actions" : [
                self.gen_report,
                (self.write_to, [report_target, "report"]),
            ]
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [
                (self.add_bookmarks, [fpath])
            ]
        })
        return task

    def add_bookmarks(self, fpath):
        self.bookmarks.update(BC.BookmarkCollection.read(fpath))

    def gen_report(self):
        return { "report" : "TODO report" }
