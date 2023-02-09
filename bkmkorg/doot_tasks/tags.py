# -*- mode:doot; -*-
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
from doot.task_mixins import ActionsMixin, BatchMixin, TargetedMixin

empty_match     : Final = re.match("","")
bib_tag_re      : Final = re.compile(r"^(\s+tags\s+=)\s+{(.+?)},$")
org_tag_re      : Final = re.compile(r"^(\*\* .+?)\s+:(\S+):$")
bookmark_tag_re : Final = re.compile(r"^(http.+?) : (.+)$")

class TagsCleaner(globber.LazyGlobMixin, globber.DirGlobMixin, globber.DootEagerGlobber, ActionsMixin, BatchMixin):
    """
    (src -> src) Clean tags in bib, org and bookmarks files,
    using tag substitution files
    """

    def __init__(self, name="tags::clean", locs=None, roots=None, rec=False, exts=None):
        # super().__init__(name, locs, roots or [locs.bibtex, locs.bookmarks, locs.orgs], rec=rec, exts=exts or [".bib", ".bookmarks", ".org"])
        super().__init__(name, locs, roots or [locs.bibtex, locs.bookmarks], rec=rec, exts=exts or [".bib", ".bookmarks", ".org"])
        self.tags = SubstitutionFile()
        self.locs.ensure("temp", "tags")

    def filter(self, fpath):
        if bool(self.glob_files(fpath)):
            return self.control.keep
        return self.control.reject

    def setup_detail(self, task):
        task.update({
            "actions" : [self.read_tags],
        })
        return task

    def task_detail(self, task):
        task.update({
            "actions" : [
                self.process_all,
            ]
        })
        return task

    def process_all(self):
        globbed = super(globber.LazyGlobMixin, self).glob_all()
        chunks  = self.chunk(globbed, 10)
        self.run_batches(*chunks)

    def batch(self, data):
        for name, fpath in data:
            self.copy_to(self.locs.temp, fpath, fn="backup")
            self.clean_orgs(fpath)
            self.clean_bibs(fpath)
            self.clean_bookmarks(fpath)

    def read_tags(self):
        targets = self.glob_files(self.locs.tags , exts=[".sub"], rec=True)
        for sub in targets:
            logging.info(f"Reading Tag Sub File: %s", sub)
            tags = SubstitutionFile.read(sub)
            self.tags += tags

    def clean_orgs(self, fpath, task):
        logging.info("Cleaning Orgs in %s", fpath)
        targets = self.glob_files(fpath ,exts=[".org"])
        if not bool(targets):
            return

        for line in fileinput.input(files=targets, inplace=True):
            try:
                match (org_tag_re.match(line) or empty_match).groups():
                    case (pre, tags):
                        tags_list = tags.split(":")
                        cleaned   = ":".join(sorted({y for x in tags_list for y in self.tags.sub(x) if bool(y)}))
                        print(f"{pre} :{cleaned}:")
                    case ():
                        print(line, end="")
                        pass

            except Exception as err:
                logging.warning("Error Processing %s (l:%s) : %s",
                                fileinput.filename(),
                                fileinput.filelineno(),
                                err)
                print(line, end="")

    def clean_bibs(self, fpath, task):
        logging.info("Cleaning Bibs in %s", fpath)
        targets = self.glob_files(fpath ,exts=[".bib"])
        if not bool(targets):
            return

        for line in fileinput.input(files=targets, inplace=True):
            try:
                match (bib_tag_re.match(line) or empty_match).groups():
                    case (pre, tags):
                        tags_list = tags.split(",")
                        cleaned = ",".join(sorted({y for x in tags_list for y in self.tags.sub(x) if bool(y)}))
                        print(f"{pre} {{{cleaned}}},")
                    case ():
                        print(line, end="")
                        pass
            except Exception as err:
                logging.warning("Error Processing %s (l:%s) : %s",
                                fileinput.filename(),
                                fileinput.filelineno(),
                                err)
                print(line, end="")

    def clean_bookmarks(self, fpath, task):
        logging.info("Cleaning Bookmarks in %s", fpath)
        targets = self.glob_files(fpath ,exts=[".bookmarks"])
        if not bool(targets):
            return

        for line in fileinput.input(files=targets, inplace=True):
            try:
                match (bookmark_tag_re.match(line.strip()) or empty_match).groups():
                    case (pre, tags):
                        tags_list = tags.split(":")
                        cleaned = " : ".join(sorted({y for x in tags_list for y in self.tags.sub(x) if bool(y)}))
                        print(f"{pre} : {cleaned}")
                    case ():
                        print(line, end="")
                        pass
            except Exception as err:
                logging.warning("Error Processing %s (l:%s) : %s",
                                fileinput.filename(),
                                fileinput.filelineno(),
                                err)
                print(line, end="")

class TagsReport(globber.LazyGlobMixin, globber.DootEagerGlobber, ActionsMixin, BatchMixin, TargetedMixin):
    """
    (src -> build) Report on tags
    """

    def __init__(self, name="tags::report", locs=None, roots=None, rec=True, exts=None):
        super().__init__(name, locs, roots or [locs.tags], rec=rec, exts=exts or [".sub"])
        self.tags = SubstitutionFile()
        self.locs.ensure("build", "temp")

    def set_params(self):
        return self.target_params()

    def task_detail(self, task):
        report     = self.locs.build / "tags.report"
        all_subs   = self.locs.temp  / "tags" / "all_subs.sub"
        all_counts = self.locs.temp  / "tags" / "all_counts.tags"
        task.update({
            "actions" : [ self.report_totals,
                          self.report_alphas,
                          self.report_subs,
                          (self.write_to, [report, ["sum_count", "subs", "alphas"]]),
                          (self.write_to, [all_subs, "all_subs"]),
                          (self.write_to, [all_counts, "all_counts"]),
                         ],
            "targets" : [ report, all_subs, all_counts ]
        })
        return task

    def read_all_tags(self):
        chunks = self.target_chunks(base=globber.LazyGlobMixin)
        self.run_batches(*chunks)

    def batch(self, data):
        for name, fpath in data:
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

        report_str = "\n".join(sorted(f"{x} : {y}" for x,y in counts.items()))

        return { "alphas" : "Tag Distribution:\n" + report_str }

    def report_subs(self):
        count = len(self.tags.substitutions)
        return { "subs" : f"Number of Subsitutions: {count}" }

class TagsIndexer(globber.LazyGlobMixin, globber.DootEagerGlobber, ActionsMixin, BatchMixin, TargetedMixin):
    """
    extract tags from all globbed bookmarks, orgs, bibtexs
    and index what tags are used in what files
    """

    def __init__(self, name="tags::index", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.bookmarks, locs.bibtex, locs.orgs], rec=True, exts=[".bookmarks", ".org", ".bib"])
        self.all_subs   = SubstitutionFile()
        self.bkmk_index = IndexFile()
        self.bib_index  = IndexFile()
        self.org_index  = IndexFile()
        self.locs.ensure("temp")

    def set_params(self):
        return self.target_params()

    def task_detail(self, task):
        existing_indices = self.locs.temp.glob("*.index")
        all_subs         = self.locs.temp / "all_subs.sub"
        new_tags         = self.locs.temp / "new_tags.tags"
        bkmk_if          = self.locs.temp / "bkmk.index"
        bib_if           = self.locs.temp / "bib.index"
        org_if           = self.locs.temp / "org.index"

        task.update({
            "actions" : [
                self.process_all_available,
                # Backup the existing index files
                (self.copy_to, [self.locs.temp, *existing_indices], {"fn": "backup"}),
                # update the combined tag index
                lambda: self.total_tags.update(self.bkmk_tags, self.bib_tags, self.org_tags),
                # Convert to strings
                lambda: {"bkmk_str"  : str(self.bkmk_index),
                         "bib_str"   : str(self.bib_index),
                         "org_str"   : str(self.org_index),
                         },
                # Write out
                (self.write_to, [bkmk_if, "bkmk_str"]),
                (self.write_to, [bib_if, "bib_str"]),
                (self.write_to, [org_if, "org_str"]),
                # Update the substitution index
                lambda: self.all_subs.update(SubstitutionFile.read(all_subs)),
                # Diff total against sub guaranteed
                self.calc_newtags, # -> new_tags
                # Write out
                (self.write_to, [new_tags, "new_tags"]),
            ],
            "file_dep" : [ all_subs ],
            "targets"  : [ bkmk_if, bib_if, org_if, new_tags ],
        })
        return task

    def process_all_available(self):
        chunks = self.target_chunks(base=globber.LazyGlobMixin)
        self.run_batches(*chunks)

    def batch(self, data):
        files = [x[1] for x in data]
        if not bool(files):
            return

        for line in fileinput.input(files=files):
            regex       = None
            splt_by     = ":"
            tags_target = None
            match pl.Path(fileinput.filename()).suffix:
                case ".bookmarks":
                    regex = bookmark_tag_re
                    tags_target = self.bkmk_index
                case ".bib":
                    regex = bib_tag_re
                    split_by = ","
                    tags_target = self.bib_index
                case ".org":
                    regex = org_tag_re
                    tags_target = self.org_index
                case _:
                    continue

            result = regex.match(line)
            if result is None:
                continue

            extracted = [(x.strip(), 1, fileinput.filename()) for x in result[1].split(split_by)]
            tags_target.update(extracted)

    def calc_newtags(self):
        all_sub_set = self.all_subs.to_set()
        new_bkmk    = self.bkmk_index.to_set() - all_sub_set
        new_bib     = self.bib_index.to_set()  - all_sub_set
        new_org     = self.org_index.to_set()  - all_sub_set

        new_tags = TagFile()
        new_tags.update(new_bkmk | new_bib | new_org)
        return { "new_tags" : str(new_tags) }

class TagsGrep(DootTasker):
    """
    grep directories slowly to build tag indices
    """

    def __init__(self, name="tags::grep", dirs=None):
        super().__init__(name, dirs)

    def task_detail(self, task):
        task.update({
            "actions" : [],
        })
        return task
