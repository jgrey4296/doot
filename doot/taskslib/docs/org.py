#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import sys
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

import doot
from doot import globber
from doot.tasker import DootTasker, ActionsMixin

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

tweet_index_file = doot.config.on_fail(".tweets", str).tool.doot.twitter.index()
file_index_file  = doot.config.on_fail(".files", str).tool.doot.twitter.file_index()
link_index_file  = doot.config.on_fail(".links", str).tool.doot.twitter.link_index()
thread_file      = doot.config.on_fail(".threads", str).tool.doot.twitter.thread_index()

empty_match = re.match("","")

# TODO thread crosslinking

class LinkCleanExtract(globber.DirGlobMixin, globber.DootEagerGlobber, ActionsMixin):
    """
    OCR all files for all thread directories,
    and extract all links into .links files
    """

    def __init__(self, name="thread::links.clean", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots, rec=True)

    def filter(self, fpath):
        if any(x.suffix == ".org" for x in fpath.iterdir()):
            return self.control.keep
        else:
            return self.control.discard

    def subtask_detail(self, task, fpath=None):
        task.update({
            "actions" : [
                # extract links to .links file
                (self.extract_links, [fpath]),
                (self.expand_and_clean_links, [fpath]),
                (self.retrieve_ocr_text, [fpath]),
            ],
            "targets" : [ fpath / link_index_file ],
        })
        return task

    def extract_links(self, fpath):
        globbed = self.glob_files(fpath)
        link_reg = re.compile(r"\[\[(.+?)\]")
        link_index = (fpath / link_index_file).open('w')
        try:
            for line in fileinput.input(files=globbed):
                result = link_reg.search(line)
                if result is None:
                    continue

                print(result[1], file=link_index)

        finally:
            link_index.close()

    def expand_and_clean_links(self, fpath):
        link_index  = fpath / link_index_file
        links       = set(link_index.read_text().split("\n"))
        clean_links = set()

        # process

        link_index.write("\n".join(clean_links))

    def retrieve_ocr_text(self, fpath):
        pass

class TweetExtract(globber.DirGlobMixin, globber.DootEagerGlobber, ActionsMixin):
    """
    glob all directories with orgs in,
    and write .tweets and .files listings
    """

    def __init__(self, name="tweets::extract", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".org"], rec=rec)
        self.permalink_re = re.compile(r":PERMALINK:\s+\[\[.+?\]\[(.+?)\]\]")

    def filter(self, fpath):
        if any(x.suffix == ".org" for x in fpath.iterdir()):
            return self.control.keep
        else:
            return self.control.discard

    def subtask_detail(self, task, fpath=None):
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
        permalinks  = set()

        for line in fileinput.input(files=globbed):
            result = self.permalink_re.search(line)
            if result:
                permalinks.add(result[1])

        tweet_index.write_text("\n".join(permalinks))

class OrgThreadCount(globber.DirGlobMixin, globber.DootEagerGlobber, ActionsMixin):
    """
    mark files with multiple threads
    """

    def __init__(self, name="org::threadcount", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".org"], rec=True)
        self.heading_re = re.compile(f"^\** ")

    def filter(self, fpath):
        if any(x.suffix == ".org" for x in fpath.iterdir()):
            return self.control.keep
        else:
            return self.control.discard

    def is_current(self, task):
        return pl.Path(task.targets[0]).exists()

    def subtask_detail(self, task, fpath=None):
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

class ThreadOrganise(globber.DirGlobMixin, globber.DootEagerGlobber, ActionsMixin):
    """
    move threads in multi thread files to their own separate count
    """

    def __init__(self, name="thread::organise", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".org"], rec=rec)
        self.total_threads   = 0
        self.multi_threads   = set()
        self.total_files_reg = re.compile(r"^Total Files: (\d+)$")
        self.header_reg      = re.compile(r"^(\**) ")

    def filter(self, fpath):
        if any(x.suffix == ".org" for x in fpath.iterdir()):
            return self.control.keep
        else:
            return self.control.discard

    def subtask_detail(self, task, fpath=None):
        task.update({
            "actions" : [
                (self.read_threadcount, [fpath]),
                (self.process_threads, [fpath]),
            ],
            "file_dep" : [fpath / thread_file],
        })
        return task

    def process_threads(self, fpath):
        if not bool(self.multi_threads):
            return

        print(f"Processing: {fpath} : Total: {self.total_threads}, {self.multi_threads}",
              file=sys.stderr)
        targets = list(self.multi_threads)
        self.multi_threads.clear()
        header_file  = fpath / "headers.org"
        current_file = None
        state        = 'header'
        header_lines = []
        new_thread   = None
        try:
            for line in fileinput.input(files=targets, inplace=True, backup=".backup"):
                if fileinput.filename() != current_file:
                    current_file = fileinput.filename()
                    try:
                        new_thread.close()
                    except AttributeError:
                        pass
                    new_thread = None
                    state = 'header'

                # Determine state
                match (self.header_reg.match(line) or empty_match).groups():
                    case ():
                        pass
                    case ("*",):
                        state = 'header'
                    case ("**",) if state == 'header' and new_thread is None: # first thread
                        state = 'first_thread'
                        new_thread = True
                    case ("**",): # new thread
                        try:
                            new_thread.close()
                        except AttributeError:
                            pass
                        self.total_threads += 1
                        new_thread_name = fpath / f"thread_{self.total_threads}.org"
                        assert(not new_thread_name.exists())
                        new_thread = new_thread_name.open('a')
                        state = 'new_thread'
                    case _: # sub levels, ignore
                        pass

                # Act on state
                match state:
                    case 'header':
                        header_lines.append(line)
                    case 'first_thread':
                        print(line, end="")
                    case 'new_thread':
                        print(line, end="", file=new_thread)
                    case _:
                        raise Exception("This shouldn't be possible")

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
            result = self.total_files_reg.match(line)
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
class OrgExport(globber.DirGlobMixin, globber.DootEagerGlobber, ActionsMixin):
    """
    Convert each thread to html
    """
    pass

class OrgEpubBuild(globber.DirGlobMixin, globber.DootEagerGlobber, ActionsMixin):
    """
    Build working epub directories in each account
    """
    pass

class ZipUser(globber.DirGlobMixin, globber.DootEagerGlobber, ActionsMixin):
    """
    Zip each account for backup
    """
    pass

##-- end todo
