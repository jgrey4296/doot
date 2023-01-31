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

import fileinput
import re
from collections import defaultdict

import doot
from bkmkorg.formats.tagfile import IndexFile, SubstitutionFile, TagFile
from doot import globber
from doot.tasker import DootTasker
from doot.task_mixins import ActionsMixin

tag_path        : Final = doot.config.on_fail("resources/tags", str).tool.doot.tags.loc()
empty_match     : Final = re.match("","")
bib_tag_re      : Final = re.compile(r"^(\s+tags\s+= ){(.+?)},$")
org_tag_re      : Final = re.compile(r"^(\*\* .+?)\s+:(.+?):$")
bookmark_tag_re : Final = re.compile(r"^(http.+?) : (.+)$")

class TagsCleaner(globber.DirGlobMixin, globber.DootEagerGlobber, ActionsMixin):
    """
    (src -> src) Clean tags in bib, org and bookmarks files,
    using tag substitution files
    """

    def __init__(self, name="tags::clean", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.bibtex, locs.bookmarks, locs.orgs], rec=rec, exts=exts or [".bib", ".bookmarks", ".org"])
        self.tags = SubstitutionFile()
        assert(self.locs.temp)
        assert(self.locs.tags)


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
            "actions" : [
                (self.copy_to, [self.locs.temp, fpath], {"fn": "backup"}),
                (self.clean_orgs, [fpath]),
                (self.clean_bibs, [fpath]),
                (self.clean_bookmarks, [fpath]),
            ],
        })
        return task

    def read_tags(self):
        for sub in self.glob_files(self.locs.tags / tag_path, exts=[".sub"]):
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
                match (bib_tag_re.match(line) or empty_match).groups():
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
                match (bookmark_tag_re.match(line) or empty_match).groups():
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

class TagsReport(globber.DootEagerGlobber, ActionsMixin):
    """
    (src -> build) Report on tags
    """

    def __init__(self, name="tags::report", locs=None, roots=None, rec=True, exts=None):
        super().__init__(name, locs, roots or [locs.tags], rec=rec, exts=exts or [".sub"])
        self.tags = SubstitutionFile()
        assert(self.locs.build)
        assert(self.locs.temp)

    def task_detail(self, task):
        report     = self.locs.build / "tags.report"
        all_subs   = self.locs.temp  / "all_subs.sub"
        all_counts = self.locs.temp  / "all_counts.tags"
        task.update({
            "actions" : [ self.report_totals,
                          self.report_alphas,
                          self.report_subs,
                          (self.write_to, [report, "sum_count", "alphas", "subs"]),
                          (self.write_to, [all_subs, "all_subs"]),
                          (self.write_to, [all_counts, "all_counts"]),
                         ],
            "targets" : [ report, all_subs, all_counts ]
        })
        return task

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
        return { "sum_count" : f"Total Count: {count}",
                 "all_subs"  : str(self.tags),
                 "all_counts": TagFile.__str__(self.tags)
                }

    def report_alphas(self):
        counts = defaultdict(lambda: 0)
        for tag in self.tags:
            counts[tag[0]] += 1

        report_str = "\n".join(f"{x} : {y}" for x,y in counts.items())

        return { "alphas" : "Tag Distribution:\n" + report_str }

    def report_subs(self):
        count = len(self.tags.substitutions)
        return { "subs" : f"Number of Subsitutions: {count}" }

class TagsIndexer(globber.DootEagerGlobber, ActionsMixin):
    """
    TODO extract tags from all globbed bookmarks, orgs, bibtexs
    and index what tags are used in what files
    """

    def __init__(self, name="tags::index", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.bookmarks, locs.bibtex, locs.orgs], rec=True, exts=[".bookmarks", ".org", ".bib"])
        self.all_subs   = SubstitutionFile()
        self.bkmk_index = IndexFile()
        self.bib_index  = IndexFile()
        self.org_index  = IndexFile()
        assert(self.locs.temp)


    def task_detail(self, task):
        existing_indices = self.locs.temp.glob("*.index")
        all_subs         = self.locs.temp / "all_subs.sub"
        new_tags         = self.locs.temp / "new_tags.tags"
        bkmk_if          = self.locs.temp / "bkmk.index"
        bib_if           = self.locs.temp / "bib.index"
        org_if           = self.locs.temp / "org.index"

        task.update({
            "actions" : [
                (self.copy_to, [self.locs.temp, *existing_indices], {"fn": "backup"}),
                lambda: self.total_tags.update(self.bkmk_tags, self.bib_tags, self.org_tags),
                lambda: {"bkmk_str"  : str(self.bkmk_index),
                         "bib_str"   : str(self.bib_index),
                         "org_str"   : str(self.org_index),
                         },
                (self.write_to, [bkmk_if, "bkmk_str"]),
                (self.write_to, [bib_if, "bib_str"]),
                (self.write_to, [org_if, "org_str"]),
                lambda: self.all_subs.update(SubstitutionFile.read(all_subs)),
                self.calc_newtags,
                (self.write_to, [new_tags, "new_tags"]),
            ],
            "file_dep" : [ all_subs ],
            "targets"  : [ bkmk_if, bib_if, org_if, new_tags ],
        })
        return task

    def subtask_detail(self, task, fpath):
        match fpath.suffix:
            case ".bookmarks":
                action = self.process_bookmarks
            case ".bib":
                action = self.process_bibtex
            case ".org":
                action = self.process_org

        task.update({
            "actions" : [(action, fpath)],
        })
        return task

    def calc_newtags(self):
        all_sub_set = self.all_subs.to_set()
        new_bkmk = self.bkmk_index.to_set() - all_sub_set
        new_bib  = self.bib_index.to_set() - all_sub_set
        new_org  = self.org_index.to_set() - all_sub_set

        new_tags = TagFile()
        new_tags.update(new_bkmk | new_bib | new_org)
        return { "new_tags" : str(new_tags) }

    def process_bookmarks(self, fpath):
        pass

    def process_bibtex(self, fpath):
        pass

    def process_org(self, fpath):
        pass
