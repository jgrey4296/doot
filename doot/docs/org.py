#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import fileinput
import logging as logmod
from collections import defaultdict
import pathlib as pl
import re
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref
from doit.action import CmdAction

import doot
from doot.utils import globber
from doot.utils.checkdir import CheckDir
from doot.utils.cmdtask import CmdTask
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

# Path Quote
pq = lambda x: quote(str(x))

tweet_index_file = doot.config.or_get(".tweets").tool.doot.twitter.index()
file_index_file  = doot.config.or_get(".files").tool.doot.twitter.file_index()
link_index_file  = doot.config.or_get(".links").tool.doot.twitter.link_index()
thread_file      = doot.config.or_get(".threads").tool.doot.twitter.thread_index()

# TODO ThreadMover - move threads in multi thread files to their own separate count
# TODO header remover
# TODO link extractor
# TODO link cleaner
# TODO extracted text insertion
# TODO Quote expander
# TODO thread crosslinking

class TweetExtract(globber.DirGlobber):

    def __init__(self, name="tweets::extract", dirs=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".org"], rec=rec)
        self.permalink_re = re.compile(r":PERMALINK:\s+\[\[.+?\]\[(.+?)\]\]")

    def filter(self, fpath):
        if any(x.suffix == ".org" for x in fpath.iterdir()):
            return self.control.keep
        else:
            return self.discard

    def subtask_detail(self, fpath, task):
        task.update({
            "actions" : [ (self.extract_tweet_ids, [fpath]),
                          (self.get_files, [fpath]),
                          ],
            "targets" : [fpath / tweet_index_file,
                         fpath / file_index_file,
                         fpath / link_index_file,
                         ],
            "clean"   : True,
                    })
        return task

    def get_files(self, fpath):
        file_dir = fpath / f"{fpath.name}_files"
        if not file_dir.exists():
            return

        file_listing = [str(x.relative_to(fpath)) for x in file_dir.iterdir()]
        (fpath / file_index_file).write_text("\n".join(file_listing))

    
    def extract_tweet_ids(self, fpath):
        # fileinput over all orgs, get the permalinks
        globbed     = self.glob_files(fpath)
        tweet_index = fpath / tweet_index_file
        permalinks  = []

        for line in fileinput.input(files=globbed):
            result = self.permalink_re.search(line)
            if result:
                permalinks.append(result[1])

        tweet_index.write_text("\n".join(permalinks))


class OrgThreadCount(globber.DirGlobber):
    """
    mark files with multiple threads
    """

    def __init__(self, name="org::threadcount", dirs=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".org"], rec=True)
        self.heading_re = re.compile(f"^\** ")

    def filter(self, fpath):
        if any(x.suffix == ".org" for x in fpath.iterdir()):
            return self.control.keep
        else:
            return self.discard

    def subtask_detail(self, fpath, task):
        task.update({
            "actions" : [ (self.check_thread_counts, [fpath]) ],
            "targets" : [fpath / thread_file],
            "clean"   : True,
        })
        return task

    def check_thread_counts(self, fpath):
        target  = fpath / thread_file
        counts  = defaultdict(lambda: [0, 0])
        total   = 0
        globbed = self.glob_fils(fpath)

        for line in fileinput.input(files=globbed):
            if not self.heading_re.match(line):
                continue

            current = pl.Path(fileinput.filename()).relative_to(fpath)
            match line.count("*"):
                case 1:
                    # file header
                    counts[current][0] += 1
                case 2:
                    # thread header
                    counts[current][1] += 1
                    total += 1
                case _:
                    pass

        summary = [f"L1: {y[0]} {x}\nL2: {y[1]} {x}" for x,y in counts.items()]
        target.write_text(f"Total: {total}\n" + "\n".join(summary))






class OrgExport(globber.DirGlobber):
    """
    Convert each thread to html
    """
    pass

class OrgEpubBuild(globber.DirGlobber):
    """
    Build working epub directories in each account
    """
    pass

class ZipUser(globber.DirGlobber):
    """
    Zip each account for backup
    """
    pass

