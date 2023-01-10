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

# TODO thread crosslinking

class LinkCleanExtract(globber.DirGlobber):
    """

    """

    def __init__(self, name="thread::links.clean", dirs=None, roots=None, rec=True):
        super().__init__(name, dirs, roots, rec=True)

    def filter(self, fpath):
        if any(x.suffix == ".org" for x in fpath.iterdir()):
            return self.control.keep
        else:
            return self.control.discard

    def subtask_detail(self, fpath, task):
        task.update({
            "actions" : [
                # read files
                # extract links to .links file
                # clean the link targets
                # Insert extracted text
            ],
                    })
        return task

class TweetExtract(globber.DirGlobber):

    def __init__(self, name="tweets::extract", dirs=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".org"], rec=rec)
        self.permalink_re = re.compile(r":PERMALINK:\s+\[\[.+?\]\[(.+?)\]\]")

    def filter(self, fpath):
        if any(x.suffix == ".org" for x in fpath.iterdir()):
            return self.control.keep
        else:
            return self.control.discard

    def subtask_detail(self, fpath, task):
        task.update({
            "actions" : [ (self.extract_tweet_ids, [fpath]),
                          (self.get_files, [fpath]),
                          ],
            "targets" : [fpath / tweet_index_file,
                         fpath / file_index_file,
                         # fpath / link_index_file,
                         ],
            "clean"   : True,
                    })
        return task

    def get_files(self, fpath):
        file_dir = fpath / f"{fpath.name}_files"
        if not file_dir.exists():
            return
        if file_dir.is_file():
            with open(pl.Path() / "file_dirs.errors", 'a') as f:
                f.write("\n" + str(fpath))
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
            return self.control.discard

    def subtask_detail(self, fpath, task):
        task.update({
            "actions" : [ (self.check_thread_counts, [fpath]) ],
            "targets" : [fpath / thread_file],
            "clean"   : True,
        })
        return task

    def check_thread_counts(self, fpath):
        target        = fpath / thread_file
        counts        = defaultdict(lambda: [0, 0])
        globbed       = [x for x in self.glob_files(fpath) if "thread" in x.stem]
        total_files   = len(globbed)
        total_threads = 0

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
                    total_threads += 1
                case _:
                    pass

        summary = [f"L1: {y[0]} {x}\nL2: {y[1]} {x}" for x,y in counts.items()]
        target.write_text(f"Total Files: {total_files}\nTotal Threads: {total_threads}\n" + "\n".join(summary))

class ThreadOrganise(globber.DirGlobber):
    """
    move threads in multi thread files to their own separate count
    """

    def __init__(self, name="thread::organise", dirs=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.data], exts=[".org"], rec=rec)
        self.total_threads = 0
        self.multi_threads = set()

    def filter(self, fpath):
        if any(x.suffix == ".org" for x in fpath.iterdir()):
            return self.control.keep
        else:
            return self.control.discard

    def subtask_detail(self, fpath, task):
        task.update({
            "actions" : [
                # read threadfile to get targets and current count
                (self.read_threadcount, [fpath]),
                (self.process_threads, [fpath]),
                # process targets into new files
                # move all headers into a header file
                     ],
            "file_dep" : [fpath / thread_file],
        })
        return task

    def process_threads(self, fpath):
        print(f"Processing: {fpath} : Total: {self.total_threads}, {self.multi_threads}")
        if not bool(self.multi_threads):
            return

        targets = list(self.multi_threads)
        self.multi_threads.clear()
        header_file  = fpath / "headers.org"
        current_file = None
        state        = 'header'
        header_lines = []
        new_thread   = None
        try:
            for line in fileinput.input(files=targets, inplace=True):
                if fileinput.filename() != current_file:
                    current_file = fileinput.filename()
                    try:
                        new_thread.close()
                    except AttributeError:
                        pass
                    new_thread = None
                    state = 'header'


                # Determine state
                match line.strip()[:3]:
                    case "" if state == 'header':
                        pass
                    case x if re.match(r"^\* ", x): # header
                        state = 'header'
                    case "** " if state == 'header' and new_thread is None: # first thread
                        state = 'first_thread'
                        new_thread = True
                    case "** ": # new thread
                        try:
                            new_thread.close()
                        except AttributeError:
                            pass
                        self.total_threads += 1
                        new_thread = (fpath / f"thread_{self.total_threads}.org").open('a')
                        state = 'new_thread'
                    case _:
                        pass

                match state:
                    case 'header':
                        header_lines.append(line)
                    case 'first_thread':
                        print(line, end="")
                    case 'new_thread':
                        print(line, end="", file=new_thread)


        finally:
            try:
                new_thread.close()
            except AttributeError:
                pass

        # After everything, write to the headers file
        with open(header_file, 'a') as f:
            f.write("\n" + "".join(header_lines))

    def read_threadcount(self, fpath):
        self.multi_threads.clear()
        threadp = fpath / thread_file
        for line in threadp.read_text().split("\n"):
            result = re.match(r"Total Files: (\d+)", line)
            if result:
                self.total_threads = int(result[1])
                continue

            result = re.match("L(\d): (\d+) (.+?)$", line)
            if not result:
                continue

            if int(result[1]) == 1 and int(result[2]) > 0:
                self.multi_threads.add(fpath / result[3].strip())
            elif int(result[2]) > 1:
                self.multi_threads.add(fpath / result[3].strip())



##-- todo
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


##-- end todo