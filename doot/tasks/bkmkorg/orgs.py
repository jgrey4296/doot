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

import re
import fileinput
from collections import defaultdict

import doot
from doit.exceptions import TaskFailed
from doot import globber
from doot.mixins.commander import CommanderMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.batch import BatchMixin
from doot.mixins.targeted import TargetedMixin
from doot.tasker import DootTasker

tweet_index_file : Final[str] = doot.config.on_fail(".tweets", str).twitter.index()
file_index_file  : Final[str] = doot.config.on_fail(".files", str).twitter.file_index()
link_index_file  : Final[str] = doot.config.on_fail(".links", str).twitter.link_index()
thread_file      : Final[str] = doot.config.on_fail(".threads", str).twitter.thread_index()

empty_match      : Final[re.Match] = re.match("","")

class TODOOrgCleaner(DelayedMixin, TargetedMixin, globber.DootEagerGlobber):
    """
    Find and format any org files
    """

    def __init__(self, name="org::clean", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.orgs], rec=rec, exts=exts or [".org"])

    def filter(self, fpath):
        return self.control.accept

    def task_detail(self, task, fpath):
        task.update({
            "actions" : []
        })
        return task

class TODOOrg2Html(DelayedMixin, TargetedMixin, globber.DootEagerGlobber):

    def __init__(self, name="org::2html", locs=None, roots=None):
        super().__init__(name, locs, roots or [locs.data], rec=True)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        return fpath.suffix(".org")

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.convert_to_html, [fpath]) ],
        })
        return task

    def convert_to_html(self, fpath):
        pass

class ThreadListings(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, BatchMixin):
    """
    glob all directories with orgs in,
    and write .tweets and .files listings
    """

    def __init__(self, name="threads::listing", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".org"], rec=rec)
        self.permalink_re = re.compile(r":PERMALINK:\s+\[\[.+?\]\[(.+?)\]\]")

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix == ".org" for x in fpath.iterdir()):
            return self.control.keep
        else:
            return self.control.discard

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.process_dir, [fpath]) ],
        })
        return task

    def sub_filter(self, fpath):
        if fpath.suffix == ".org":
            return self.globc.accept
        return self.globc.discard

    def process_dir(self, fpath):
        logging.info("Processing: %s", fpath)
        file_index = fpath / file_index_file
        tweet_index = fpath / tweet_index_file

        file_listing = self.get_files(fpath)
        permalinks   = set()

        for line in fileinput.input(files=self.glob_target(fpath, fn=self.sub_filter)):
            if fileinput.isfirstline():
                logging.info("Processing: %s", fileinput.filename())

            result = self.permalink_re.search(line)
            if result:
                permalinks.add(result[1])

        file_index.write_text("\n".join(file_listing))
        tweet_index.write_text("\n".join(permalinks))

    def get_files(self, fpath):
        """
        make a file listing for a user
        """
        file_dir   = fpath / f"{fpath.name}_files"
        if not file_dir.exists():
            return []

        if file_dir.is_file():
            with open(pl.Path() / "file_dirs.errors", 'a') as f:
                f.write("\n" + str(fpath))
            return []

        return [str(x.relative_to(fpath)) for x in file_dir.iterdir()]

class OrgMultiThreadCount(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, BatchMixin):
    """
    Count threads in files, make a thread file (default: .threads)
    """

    def __init__(self, name="org::threadcount", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".org"], rec=True)
        self.heading_re = re.compile(f"^\** ")

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix == ".org" for x in fpath.iterdir()):
            return self.control.keep
        return self.control.discard

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.count_threads, [fpath]) ],
        })
        return task

    def sub_filter(self, fpath):
        if fpath.is_file() and fpath.suffix == ".org":
            return self.globc.accept
        return self.globc.discard

    def count_threads(self, fpath):
        logging.info("Counting Threadings for: %s", fpath)
        globbed        = [x for x in self.glob_target(fpath, fn=self.sub_filter)]
        thread_listing = fpath / thread_file
        counts         = defaultdict(lambda: [0, 0])
        total_files    = len(globbed)
        total_threads  = 0
        logging.info("Globbed: %s", len(globbed))
        for line in fileinput.input(files=globbed):
            if fileinput.isfirstline():
                logging.info("Processing: %s", fileinput.filename())

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
        thread_listing.write_text(f"Total Files: {total_files}\nTotal Threads: {total_threads}\n" + "\n".join(summary))

class ThreadOrganise(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, BatchMixin):
    """
    move threads in multi thread files to their own separate count
    """

    def __init__(self, name="thread::organise", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.data], exts=[".org"], rec=rec)
        self.total_threads   = 0
        self.multi_threads   = set()
        self.total_files_reg = re.compile(r"^Total Files: (\d+)$")
        self.header_reg      = re.compile(r"^(\**) ")

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix == ".org" for x in fpath.iterdir()):
            return self.control.keep
        else:
            return self.control.discard

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [
                (self.read_threadcount, [fpath]),
                (self.process_threads, [fpath]),
            ],
        })
        return task

    def read_threadcount(self, fpath):
        threadp = fpath / thread_file
        self.multi_threads.clear()
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

    def process_threads(self, fpath):
        if not bool(self.multi_threads):
            return

        logging.info(f"Processing: {fpath} : Total: {self.total_threads}, {len(self.multi_threads)}")

        targets = list(self.multi_threads)
        self.multi_threads.clear()

        header_file  = fpath / "headers.org"
        current_file = None
        state        = 'header'
        header_lines = []
        new_thread   = None
        # Run through lines in multi thread files,
        # as a state machine, moving extra threads into new files
        try:
            for line in fileinput.input(files=targets, inplace=True, backup=".backup"):
                if fileinput.isfirstline():
                    current_file = fileinput.filename()
                    try:
                        new_thread.close()
                    except AttributeError:
                        pass
                    new_thread = None
                    state      = 'header'

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

class ThreadImageOCR(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, BatchMixin):
    """
    OCR all files for all thread directories,
    and extract all links into .links files
    """

    def __init__(self, name="thread::ocr", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots, rec=True)
        self.link_reg   = re.compile(r"\[\[(.+?)\]")

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and any(x.suffix == ".org" for x in fpath.iterdir()):
            return self.control.keep
        return self.control.discard

    def subtask_detail(self, task, fpath=None):
        task.update({
            "actions" : [ (self.process_files, [fpath]) ],
        })
        return task

    def sub_filter(self, fpath):
        if fpath.is_file():
            return self.globc.accept
        return self.globc.discard

    def process_files(self, fpath):
        chunks = self.chunk(self.glob_target(fpath, fn=self.sub_filter))
        self.run_batches(*chunks)

    def batch(self, data):
        for fpath in data:
            link_index = fpath / link_index_file
            links      = self.extract_links(fpath)
            link_index.write_text("\n".join(links))

            cleaned = self.expand_and_clean_links(fpath, links)
            link_index.write_text("\n".join(links))

            self.retrieve_ocr_text(fpath)

    def extract_links(self, fpath) -> list:
        """
        For all files in the dir,
        """
        globbed    = self.glob_files(fpath)
        if not bool(globbed):
            return []

        links      = []
        for line in fileinput.input(files=globbed):
            result = self.link_reg.search(line)
            if result is None:
                continue

            links.append(result[1])

        return links

    def expand_and_clean_links(self, fpath, links) -> list:
        clean_links = set()
        # process
        return list(clean_links)

    def retrieve_ocr_text(self, fpath) -> list:
        """
        Get all txt files in the files dir, and... map img -> txt
        """
        file_path = fpath / f"{fpath.name}_files"
        if not file_path.exists():
            return []

        return []
