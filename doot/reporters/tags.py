#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
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

empty_match     : Final[re.Match]   = re.match("","")
bib_tag_re      : Final[re.Pattern] = re.compile(r"^(\s+tags\s+=)\s+{(.+?)},$")
org_tag_re      : Final[re.Pattern] = re.compile(r"^(\*\* .+?)\s+:(\S+):$")
bookmark_tag_re : Final[re.Pattern] = re.compile(r"^(http.+?) : (.+)$")

class TagsReport(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, BatchMixin, FilerMixin):
    """
    (src -> build) Report on tags
    """

    def __init__(self, name="tags::report", locs=None, roots=None, rec=True, exts=None):
        super().__init__(name, locs, roots or [locs.tags], rec=rec, exts=exts or [".sub"])
        self.tags = SubstitutionFile()
        self.locs.ensure("build", "temp", task=name)

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
