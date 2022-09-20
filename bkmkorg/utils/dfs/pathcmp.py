#/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
from filecmp import cmpfiles
import logging as logmod
import pathlib as pl
import stat
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from filecmp import DEFAULT_IGNORES
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
##-- end logging

class PathCmp:
    """ A pathlib based reimplementation of the python stdlib's filecmp.dircmp class

    PathCmp(a, b, ignore=None, hide=None)
      A and B are directories.
      IGNORE is a list of names to ignore,
        defaults to DEFAULT_IGNORES.
      HIDE is a list of names to hide

    High level usage:
      x = dircmp(dir1, dir2)
      x.report() -> prints a report on the differences between dir1 and dir2
       or
      x.report_partial_closure() -> prints report on differences between dir1
            and dir2, and reports on common immediate subdirectories.
      x.report_full_closure() -> like report_partial_closure,
            but fully recursive.

    Attributes:
     left_list, right_list: The files in dir1 and dir2,
        filtered by hide and ignore.
     common: a list of names in both dir1 and dir2.
     left_only, right_only: names only in dir1, dir2.
     common_dirs: subdirectories in both dir1 and dir2.
     common_files: files in both dir1 and dir2.
     common_funny: names in both dir1 and dir2 where the type differs between
        dir1 and dir2, or the name is not stat-able.
     same_files: list of identical files.
     diff_files: list of filenames which differ.
     funny_files: list of files which could not be compared.
     subdirs: a dictionary of dircmp instances (or MyDirCmp instances if this
       object is of type MyDirCmp, a subclass of dircmp), keyed by names
       in common_dirs.
     """

    def __init__(self, a:str|pl.Path, b:str|pl.Path, ignore:None|list[str]=None, hide:None|list[pl.Path]=None):
        self.left                           = pl.Path(a)
        self.right                          = pl.Path(b)
        self.hide                           = hide   or []
        self.ignore                         = ignore or DEFAULT_IGNORES

        self.left_list    : list[pl.Path]   = []
        self.right_list   : list[pl.Path]   = []

        self.left_only    : list[pl.Path]   = []
        self.right_only   : list[pl.Path]   = []

        self.common       : list[str]       = []
        self.common_dirs  : list[str]       = []
        self.common_files : list[str]       = []
        self.common_funny : list[str]       = []

        self.same_files   : list[pl.Path]   = []
        self.diff_files   : list[pl.Path]   = []
        self.funny_files  : list[pl.Path]   = []
        self.subdirs      : dict[str, Self] = {}

    def __call__(self):
        # Run Phases:
        self.phase0()
        self.phase1()
        self.phase2()
        self.phase3()
        self.phase4()

    def phase0(self): # Compare everything except common subdirectories
        self.left_list  = [x for x in self.left.iterdir() if x.stem not in self.hide+self.ignore]
        self.right_list = [x for x in self.right.iterdir() if x.stem not in self.hide+self.ignore]

    def phase1(self): # Compute common names
        a = { str(x.relative_to(self.left)) : x for x in self.left_list }
        b = { str(x.relative_to(self.right)) : x for x in self.right_list }

        self.common     = a.keys() & b.keys()
        self.left_only  = [a[x] for x in a.keys() - b.keys()]
        self.right_only = [b[x] for x in b.keys() - a.keys()]

    def phase2(self): # Distinguish files, directories, funnies
        for x in self.common:
            a_path = self.left / x
            b_path = self.right / x

            if a_path.is_dir() and b_path.is_dir():
                self.common_dirs.append(x)
            elif a_path.is_file() and b_path.is_file and a_path.suffix == b_path.suffix:
                self.common_files.append(x)
            else:
                self.common_funny.append(x)

    def phase3(self): # Find out differences between common files
        same, diff, funny = cmpfiles(str(self.left), str(self.right), self.common_files)
        self.same_files   += same
        self.diff_files   += diff
        self.funny_files  += funny

    def phase4(self): # Find out differences between common subdirectories
        # A new dircmp (or MyDirCmp if dircmp was subclassed) object is created
        # for each common subdirectory,
        # these are stored in a dictionary indexed by filename.
        # The hide and ignore properties are inherited from the parent
        for x in self.common_dirs:
            a_x = self.left / x
            b_x = self.right / x
            self.subdirs[x]  = self.__class__(a_x, b_x, self.ignore, self.hide)

    def phase4_closure(self): # Recursively call phase4() on subdirectories
        self.phase4()
        for sd in self.subdirs.values():
            sd.phase4_closure()

    def report(self): # Print a report on the differences between a and b
        # Output format is purposely lousy
        print('diff', self.left, self.right)
        if self.left_only:
            self.left_only.sort()
            print('Only in', self.left, ':', self.left_only)
        if self.right_only:
            self.right_only.sort()
            print('Only in', self.right, ':', self.right_only)
        if self.same_files:
            self.same_files.sort()
            print('Identical files :', self.same_files)
        if self.diff_files:
            self.diff_files.sort()
            print('Differing files :', self.diff_files)
        if self.funny_files:
            self.funny_files.sort()
            print('Trouble with common files :', self.funny_files)
        if self.common_dirs:
            self.common_dirs.sort()
            print('Common subdirectories :', self.common_dirs)
        if self.common_funny:
            self.common_funny.sort()
            print('Common funny cases :', self.common_funny)

    def report_partial_closure(self): # Print reports on self and on subdirs
        self.report()
        for sd in self.subdirs.values():
            print()
            sd.report()

    def report_full_closure(self): # Report on self and subdirs recursively
        self.report()
        for sd in self.subdirs.values():
            print()
            sd.report_full_closure()



