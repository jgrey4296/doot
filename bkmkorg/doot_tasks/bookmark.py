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
from bkmkorg.bookmarks import database_fns as db_fns
from doot import globber
from doot.tasker import ActionsMixin, DootTasker

pl_expand : Final = lambda x: pl.Path(x).expanduser().resolve()

databse   : Final = doot.config.on_fail("places.sqlite", str).tools.doot.bookmarks.database_name()

class BookmarksUpdate(DootTasker, ActionsMixin):
    """
    ( -> src ) copy firefox bookmarks databases, extract, merge with bookmarks file
    """

    def __init__(self, name="bkmk::update", locs=None):
        super().__init__(name, locs)
        self.database                                      = database
        self.new_collections : list[BC.BookmarkCollection] = []
        self.total : BC.BookmarkCollection                 = None
        assert(self.locs.firefox)
        assert(self.locs.src)
        assert(self.locs.temp)


    def task_detail(self, task):
        dbs         = self.locs.firefox.rglob(self.database)
        bkmks       = self.locs.src / "total.bookmarks"
        task.update({
            "actions" : [
                (self.copy_to, [self.locs.temp, bkmks], {"is_backup": True}),
                (self.copy_to, [self.locs.temp, *dbs], {"fn": lambda d,x: d / f"{x.parent.name}_{x.name}"})
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
        for db_file in self.locs.temp.glob("*.sqlite"):
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

class BookmarksCleaner(DootTasker, ActionsMixin):
    """
    clean bookmarks file, removing duplicates, stripping urls
    """

    def __init__(self, name="bkmk::clean", locs=None):
        super().__init__(name, locs)
        self.total = None
        assert(self.locs.temp)
        assert(self.locs.src)

    def task_detail(self, task):
        task.update({
            "actions"  : [
                (self.copy_to, [self.locs.temp, fpath], {"fn": lambda d,x: d / f"{x.name}.backup}"}),
                (self._merge, [fpath]),
                lambda: {"merged": str(self.total)},
                (self.write_to, [fpath, "merged"]),)
            ],
            "file_dep" : [ self.locs.src / "total.bookmarks" ],
        })
        return task

    def _merge(self, fpath):
        self.total = BC.BookmarkCollection.read(fpath)
        self.total.merge_duplicate()

class BookmarksSplit(DootTasker, ActionsMixin):
    """
    TODO Create several bookmarks files of selections
    """
    pass

class BookmarksReport(globber.DootEagerGlobber, ActionsMixin):
    """
    TODO Generate reports on bookmarks
    """

    def __init__(self, name="bkmk::report", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.bookmarks], rec=rec, exts=exts or [".bookmarks"])
        self.bookmarks = BC.BookmarkCollection()
        assert(self.locs.build)

    def filter(self, fpath):
        return self.control.accept

    def task_detail(self, task):
        report_target = self.locs.build / "bookmarks.report"
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
