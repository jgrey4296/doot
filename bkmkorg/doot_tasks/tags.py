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
from collections import defaultdict
import fileinput
import doot
from doot.tasker import DootTasker
from doot import globber

from bkmkorg.file_formats.tagfile import SubstitutionFile

tag_path = doot.config.or_get("resources/tags").tool.doot.tags.loc()

empty_match     = re.match("","")
# groups: pre, tags, post
bib_tag_re      = re.compile(r"^(\s+tags\s+= ){(.+?)},$")
org_tag_re      = re.compile(r"^(** .+?)\s+:(.+?):$")
bookmark_tag_re = re.compile(r"^(http.+?) : (.+)$")

class TagsCleaner(globber.DirGlobber):
    """
    (src -> src) Clean tags in bib, org and bookmarks files,
    using tag substitution files
    """
    def __init__(self, name="", dirs=None, roots=None, rec=False, exts=None):
        super().__init__(name, dirs, roots or [dirs.src], rec=rec, exts=exts or [".bib", ".bookmarks", ".org"])
        self.tags = SubstitutionFile()

    def filter(self, fpath):
        if bool(self.glob_files(fpath)):
            return self.control.keep
        return self.control.reject

    def setup_detail(self, task):
        task.update({
            "actions" : [self.read_tags],
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.clean_orgs, [fpath]),
                          (self.clean_bibs, [fpath]),
                          (self.clean_bookmarks, [fpath]),
                         ],
        })
        return task

    def read_tags(self):
        for sub in self.glob_files(self.dirs.data / tag_path, exts=[".sub"]):
            logging.info(f"Reading Tag Sub File: %s", sub)
            tags = SubstitutionFile.read(sub)
            self.tags += tags

    def clean_orgs(self, task, fpath):
        logging.info("Cleaning Orgs in %s", fpath)
        for line in fileinput.input(files=self.glob_files(fpath, exts=[".org"]),
                                    inplace=True):
            try:
                match (org_tag_re.match(line) or empty_match).groups():
                    case (pre, tags):
                        tags_list = tags.split(":")
                        cleaned = ":".join({self.tags.sub(x) for x in tags_list})
                        print(f"{pre} :{cleaned}:")
                    case ():
                        print(line)
                        pass
            except Exception as err:
                logging.warning("Error Processing %s (l:%s) : %s",
                                fileinput.filename(),
                                fileinput.filelineno(),
                                err)
                print(line)


    def clean_bibs(self, task, fpath):
        logging.info("Cleaning Bibs in %s", fpath)
        for line in fileinput.input(files=self.glob_files(fpath, exts=[".bib"]),
                                    inplace=True):
            try:
                match (org_tag_re.match(line) or empty_match).groups():
                    case (pre, tags):
                        tags_list = tags.split(",")
                        cleaned = ",".join({self.tags.sub(x) for x in tags_list})
                        print(f"{pre}{{{cleaned}}},")
                    case ():
                        print(line)
                        pass
            except Exception as err:
                logging.warning("Error Processing %s (l:%s) : %s",
                                fileinput.filename(),
                                fileinput.filelineno(),
                                err)
                print(line)

    def clean_bookmarks(self, task, fpath):
        logging.info("Cleaning Bookmarks in %s", fpath)
        for line in fileinput.input(files=self.glob_files(fpath, exts=[".bookmarks"]),
                                    inplace=True):
            try:
                match (org_tag_re.match(line) or empty_match).groups():
                    case (pre, tags):
                        tags_list = tags.split(":")
                        cleaned = " : ".join({self.tags.sub(x.strip()) for x in tags_list})
                        print(f"{pre} : {{{cleaned}}}")
                    case ():
                        print(line)
                        pass
            except Exception as err:
                logging.warning("Error Processing %s (l:%s) : %s",
                                fileinput.filename(),
                                fileinput.filelineno(),
                                err)
                print(line)


class TagsReport(globber.EagerFileGlobber):
    """
    (src -> build) Report on tags
    """
    def __init__(self, name="tags::report", dirs=None, roots=None, rec=True, exts=None):
        super().__init__(name, dirs, roots or [dirs.src], rec=rec, exts=exts or [".sub"])
        self.tags = SubstitutionFile()


    def task_detail(self, task):
        task.update({
            "actions" : [ self.report_totals,
                          self.report_alphas,
                          self.create_report,
                          self.write_report,
                         ],
            "targets" : [ self.dirs.build / "tags.report"]
        })
    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.read_tags, [fpath]) ]
        })
        return task

    def read_tags(self, fpath):
        tags = SubstitutionFile.read(fpath)
        self.tags += tags


    def report_totals(self):
        count = len(self.tags)
        return { "totals" : f"Total Count: {count}" }

    def report_alphas(self):
        counts = defaultdict(lambda: 0)
        for tag in self.tags:
            counts[tag[0]] += 1

        report_str = "\n".join(f"{x} : {y}" for x,y in counts.items())

        return { "alphas" : "Tag Distribution:\n" + report_str }


    def report_subs(self):
        count = len(self.tags.mapping)
        return { "substitutions" : f"Number of Subsitutions: {count}" }

    def create_report(self, task):
        """
        Accumulate report components into a single string
        """
        total = "\n--------------------\n".join(self.task.values.values())
        return { "report_total" : total }

    def write_report(self, task):
        target = self.dirs.build / "tags.report"
        target.write(task.values['report_total'])

class TagsIndexer(globber.EagerFileGlobber):
    """
    extract tags from all globbed bookmarks, orgs, bibtexs
    """
    def __init__(self, name="tags::index", dirs=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], rec=True, exts=[".bookmarks", ".org", ".bib"])

    def subtask_detail(self, task, fpath):
        match fpath.suffix:
            case ".bookmarks":
                pass
            case ".bib":
                pass
            case ".org":
                pass

        task.update({

            "actions" : [],
        })
        return task

    def process_bookmarks(self, fpath):
        pass

    def process_bibtex(self, fpath):
        pass

    def process_org(self, fpath):
        pass
