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
from doot.tasker import DootTasker
from doot import globber

from bkmkorg.bookmarks.database_fns import extract

firefox = doot.config.or_get("~/Library/ApplicationSupport/Firefox").tools.doot.bookmarks.firefox_loc()
databse = doot.config.or_get("places.sqlite").tools.doot.bookmarks.database_name()

class BookmarksUpdate(DootTasker):
    """
    ( -> src ) copy firefox bookmarks databases, extract, merge with bookmarks file
    """

    def __init__(self, name="bookmarks::update", dirs=None):
        super().__init__(name, dirs)
        self.firefox                                       = pl.Path(firefox).expanduser().resolve()
        self.database                                      = database
        self.new_collections : list[BC.BookmarkCollection] = []
        self.total : BC.BookmarkCollection                 = None

    def task_detail(self, task):
        task.update({
            "actions" : [ self.get_databases,
                          self.load_and_extract,
                          self.load_and_merge,
                          self.update_bookmarks
                         ],
            "file_dep" : [ self.dirs.src / "total.bookmarks" ],
        })
        return task

    def get_databases(self):
        """
        copy all bookmark databases to the temp dir
        """
        for db_src in self.firefox.rglob(self.database):
            shutil.copy(db_src, self.dirs.temp / f"{db_src.parent.name}_{db_src.name}")

    def load_and_extract(self):
        """
        start pony, load db, extract, for each sqlite
        """
        for db_file in self.dirs.temp.glob("*.sqlite"):
            self.new_collections.append(extract(db_file))

    def load_and_merge(self, dependencies, task):
        """
        load total.bookmarks, merge extracted
        """
        self.total = BC.BookmarkCollection.read(dependencies[0])
        original_amnt = len(self.total)
        for extracted in self.new_collections:
            self.total += collection
            self.total.merge_duplicates()

    def update_bookmarks(self, dependencies, task):
        """
        save the updated total.bookmarks
        """
        fpath = pl.Path(dependencies[0])
        fpath.rename(self.dirs.temp / f"{fpath.name}.backup")
        fpath.write(str(self.total))

class BookmarksCleaner(DootTasker):
    """
    clean bookmarks file, removing duplicates, stripping urls
    """

    def __init__(self, name="bookmarks::clean", dirs=None):
        super().__init__(name, dirs)

    def task_detail(self, task):
        task.update({
            "actions" : [ self.load_merge_write ],
            "file_dep" : [ self.dirs.src / "total.bookmarks" ],
        })
        return task

    def load_bookmarks(self, dependencies):
        fpath = pl.Path(dependencies[0])
        total = BC.BookmarkCollection.read(fpath)
        total.merge_duplicate()
        fpath.rename(self.dirs.temp / f"{fpath.name}.backup")
        fpath.write_text(str(total))

class BookmarksSplit(DootTasker):
    """
    Create several bookmarks files of selections
    """
    pass

class BookmarksReport(DootTasker):
    """
    Generate reports on bookmarks
    """
    pass
