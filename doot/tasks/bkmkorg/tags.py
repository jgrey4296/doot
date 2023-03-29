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
from doot.utils.formats.tagfile import IndexFile, SubstitutionFile, TagFile
from doot import globber
from doot.tasker import DootTasker
from doot.mixins.batch import BatchMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.filer import FilerMixin

empty_match     : Final = re.match("","")
bib_tag_re      : Final = re.compile(r"^(\s+tags\s+=)\s+{(.+?)},$")
org_tag_re      : Final = re.compile(r"^(\*\* .+?)\s+:(\S+):$")
bookmark_tag_re : Final = re.compile(r"^(http.+?) : (.+)$")

class TagsCleaner(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, BatchMixin, FilerMixin):
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
        if fpath.is_file():
            return self.control.keep
        return self.control.discard

    def setup_detail(self, task):
        task.update({
            "actions" : [self.read_tags],
        })
        return task

    def subtask_detail(self, task, fpath):
        task['actions'].append((self.copy_to, [self.locs.temp, fpath], {fn:"backup"}))
        match fpath.suffix:
            case ".bib":
                task['actions'].append( (self.clean_bib, [fpath]) )
            case ".bookmarks":
                task['actions'].append( (self.clean_bookmark, [fpath]) )
            case ".org":
                task['actions'].append( (self.clean_org, [fpath]) )
        return task

    def read_tags(self):
        targets = self.glob_target(self.locs.tags , exts=[".sub"], rec=True, fn=lambda x: x.is_file())
        for sub in targets:
            logging.info(f"Reading Tag Sub File: %s", sub)
            tags = SubstitutionFile.read(sub)
            self.tags += tags

    def clean_org(self, fpath):
        logging.info("Cleaning Org: %s", fpath)
        for line in fileinput.input(files=[ fpath ], inplace=True):
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

    def clean_bib(self, fpath):
        logging.info("Cleaning Bib: %s", fpath)
        for line in fileinput.input(files=[fpath], inplace=True):
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

    def clean_bookmarks(self, fpath):
        logging.info("Cleaning Bookmarks in %s", fpath)
        for line in fileinput.input(files=[fpath], inplace=True):
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

class TagsReport(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, BatchMixin, FilerMixin):
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
        tag_dir    = self.locs.temp  / "tags"
        all_subs   = tag_dir / "all_subs.sub"
        all_counts = tag_dir / "totals.tags"
        task.update({
            "actions" : [ self.report_totals, # -> {sum_count, all_subs, all_counts}
                          self.report_alphas, # -> {alphas}
                          self.report_subs,   # -> {subs}
                         (self.mkdirs, [tag_dir]),
                         (self.write_to, [report, ["sum_count", "subs", "alphas"]]),
                         (self.write_to, [all_subs, "all_subs"]),
                         (self.write_to, [all_counts, "all_counts"]),
                     ],
            "targets" : [ report, all_subs, all_counts ]
        })
        return task

    def filter(self, fpath):
        if fpath.is_file():
            return self.globc.keep
        return self.globc.discard

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.read_tag_file, [fpath]) ],
        })
        return task

    def read_tag_file(self, fpath):
        logging.info("Reading: %s", fpath)
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

class TagsIndexer(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, BatchMixin, FilerMixin):
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

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.process_file, [fpath]) ],
        })
        return tas

    def process_file(self, fpath):
        logging.info("Indexing: %s", fpath)
        for line in fileinput.input(files=[fpath]):
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

class TODOTagsGrep(DootTasker, FilerMixin):
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
