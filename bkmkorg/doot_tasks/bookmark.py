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

import doot
from doot.tasker import DootTasker, DootActions
from doot import globber

from bkmkorg.bookmarks import database_fns as db_fns

firefox = doot.config.or_get("~/Library/ApplicationSupport/Firefox").tools.doot.bookmarks.firefox_loc()
databse = doot.config.or_get("places.sqlite").tools.doot.bookmarks.database_name()

class BookmarksUpdate(DootTasker, DootActions):
    """
    ( -> src ) copy firefox bookmarks databases, extract, merge with bookmarks file
    """

    def __init__(self, name="bkmk::update", dirs=None):
        super().__init__(name, dirs)
        self.firefox                                       = pl.Path(firefox).expanduser().resolve()
        self.database                                      = database
        self.new_collections : list[BC.BookmarkCollection] = []
        self.total : BC.BookmarkCollection                 = None

    def task_detail(self, task):
        dbs         = self.firefox.rglob(self.database)
        working_dir = self.dirs.temp
        bkmks       = self.dirs.src / "total.bookmarks"
        task.update({
            "actions" : [
                (self.copy_to, [self.dirs.temp, bkmks], {"is_backup": True}),
                (self.copy_to, [self.dirs.temp, *dbs], {"fn": lambda d,x: d / f"{x.parent.name}_{x.name}"})
                self._extract,
                self._merge,
                lambda: { "merged": str(self.total)},
                (self.write_to, [bkmks, "merged"]),
            ],
            "file_dep" : [ bkmks ],
        })
        return task

    def _extract(self):
        """
        start pony, load db, extract, for each sqlite
        """
        for db_file in self.dirs.temp.glob("*.sqlite"):
            self.new_collections.append(db_fns.extract(db_file))

    def _merge(self, dependencies, task):
        """
        load total.bookmarks, merge extracted
        """
        self.total = BC.BookmarkCollection.read(dependencies[0])
        original_amnt = len(self.total)
        for extracted in self.new_collections:
            self.total += collection
            self.total.merge_duplicates()

class BookmarksCleaner(DootTasker, DootActions):
    """
    clean bookmarks file, removing duplicates, stripping urls
    """

    def __init__(self, name="bkmk::clean", dirs=None):
        super().__init__(name, dirs)
        self.total = None

    def task_detail(self, task):
        task.update({
            "actions"  : [
                (self.copy_to, [self.dirs.temp, fpath], {"fn": lambda d,x: d / f"{x.name}.backup}"}),
                (self._merge, [fpath]),
                lambda: {"merged": str(self.total)},
                (self.write_to, [fpath, "merged"]),)
            ],
            "file_dep" : [ self.dirs.src / "total.bookmarks" ],
        })
        return task

    def _merge(self, fpath):
        self.total = BC.BookmarkCollection.read(fpath)
        self.total.merge_duplicate()

class BookmarksSplit(DootTasker, DootActions):
    """
    Create several bookmarks files of selections
    """
    pass

class BookmarksReport(globber.EagerFileGlobber, DootActions):
    """
    Generate reports on bookmarks
    """

    def __init__(self, name="bkmk::report", dirs=None, roots=None, rec=False, exts=None):
        super().__init__(name, dirs, roots or [dirs.src], rec=rec, exts=exts or [".bookmarks"])
        self.bookmarks = BC.BookmarkCollection()

    def filter(self, fpath):
        return self.control.accept

    def task_detail(self, task):
        report_target = self.dirs.build / "bookmarks.report"
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
                lambda: self.bookmarks.update(BC.BookmarkCollection.read(fpath)),
            ]
        })
        return task

    def gen_report(self):

        return { "report" : "" }
