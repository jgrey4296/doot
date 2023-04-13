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

import doot
from doot import globber, tasker
from doot.mixins.batch import BatchMixin
from doot.mixins.bibtex import clean as bib_clean
from doot.mixins.bibtex import utils as bib_utils
from doot.mixins.bibtex.load_save import BibLoadSaveMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.pdf import PdfMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.web import WebMixin
from doot.tasker import DootTasker
from doot.tasks.files.backup import BackupTask
from doot.utils.formats.timelinefile import TimelineFile
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from collections import defaultdict

import doot
from doot import globber, tasker
from doot.mixins.batch import BatchMixin
from doot.mixins.bibtex import clean as bib_clean
from doot.mixins.bibtex import utils as bib_utils
from doot.mixins.bibtex.load_save import BibLoadSaveMixin
from doot.mixins.commander import CommanderMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.pdf import PdfMixin
from doot.mixins.targeted import TargetedMixin
from doot.mixins.web import WebMixin
from doot.tasker import DootTasker
from doot.tasks.files.backup import BackupTask
from doot.utils.formats.timelinefile import TimelineFile

min_tag_timeline     : Final[int] = doot.config.on_fail(10, int).bibtex.min_timeline()
stub_exts            : Final[list] = doot.config.on_fail([".pdf", ".epub", ".djvu", ".ps"], list).bibtex.stub_exts()
clean_in_place       : Final[bool] = doot.config.on_fail(False, bool).bibtex.clean_in_place()
wayback_wait         : Final[int] = doot.config.on_fail(10, int).bibtex.wayback_wait()
acceptible_responses : Final[list] = doot.config.on_fail(["200"], list).bibtex.accept_wayback()
ENT_const            : Final[str] = 'ENTRYTYPE'

class BibtexReport(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, FilerMixin, BatchMixin, BibLoadSaveMixin, bib_clean.BibFieldCleanMixin, bib_clean.BibPathCleanMixin):
    """
    (src -> build) produce reports on the bibs found
    """

    def __init__(self, name="report::bibtex", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.bibtex], rec=rec, exts=[".bib"])
        self.locs.update(timelines=self.locs.build / "timelines")
        self.locs.ensure("pdfs", "timelines", task=name)

        self.db                             = None
        self.tag_file_mapping               = defaultdict(list)
        self.tag_counts                     = defaultdict(lambda: 0)
        self.year_counts                    = defaultdict(lambda: 0)
        self.type_counts                    = defaultdict(lambda: 0)
        self.files_counts                   = defaultdict(lambda: 0)
        self.authors : set[tuple[str, str]] = set()
        self.editors : set[tuple[str, str]] = set()

    def setup_detail(self, task):
        task.update({
            "actions": [ (self.bc_load_db, [[], lambda x: x]) ]
        })
        return task

    def task_detail(self, task):
        years_target  = self.locs.build / "years.report"
        author_target = self.locs.build / "authors.report"
        editor_target = self.locs.build / "editors.report"
        types_target  = self.locs.build / "types.report"
        files_target  = self.locs.build / "files.report"

        task.update({
            "actions" : [

                ##-- report on authors
                lambda:      { "author_max" : max((len(x[0]) for x in self.authors), default=0) },
                lambda task: { "author_lines" : [f"{last:<{task.values['author_max']}}{first}" for last,first in self.authors] },
                lambda task: { "authors" : "\n".join(sorted(task.values['author_lines'], key=lambda x: x[0].lower())) },
                (self.write_to, [author_target, "authors"]),
                ##-- end report on authors

                ##-- report on editors
                lambda:   { "editor_max" : max((len(x[0]) for x in self.editors), default=0) },
                lambda task: { "editor_lines" : [f"{last:<{task.values['editor_max']}}{first}" for last,first in self.editors] },
                lambda task: { "editors" : "\n".join(sorted(task.values['editor_lines'], key=lambda x: x[0].lower())) },
                (self.write_to, [editor_target, "editors"]),
                ##-- end report on editors

                ##-- report on years
                self.gen_years,
                (self.write_to, [years_target, "years"]),
                ##-- end report on years

                ##-- report on entry types
                lambda: { "types" : "\n".join(sorted(f"{x:<15} : {y}" for x,y in self.type_counts.items())) },
                (self.write_to, [types_target, "types"]),
                ##-- end report on entry types

                ##-- report on entry files
                lambda: { "files" : "\n".join(sorted(f"{x:<15} : {y}" for x,y in self.files_counts.items())) },
                (self.write_to, [files_target, "files"]),
                ##-- end report on entry files

                self.write_timelines,
            ],
            "targets" : [ years_target, author_target, editor_target, types_target, files_target, self.locs.timelines ],
            "clean" : True,
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [
                (self.load_bib, [fpath]),
            ]
        })
        return task

    def load_bib(self, fpath):
        self.db = self.bc_load_db([fpath], fn=self.process_entry, db=self.db)

    def process_entry(self, entry):
        try:
            self.bc_expand_paths(entry, self.locs.pdfs)
            self.bc_tag_split(entry)
            self.bc_split_names(entry)

            assert(all(x in entry for x in ['__paths', '__split_names', '__as_unicode', '__tags']))
            self.collect_tags(entry)
            self.collect_authors_and_editors(entry)
            self.year_counts[entry['year']]    += 1
            self.type_counts[entry[ENT_const]] += 1

            if bool(entry['__paths']):
                self.files_counts[entry[ENT_const]] += 1

        except Exception as err:
            logging.warning("Failure to process %s : %s", entry['ID'], err)
        finally:
            return entry

    def collect_tags(self, entry):
        """
        Get all tags from all entries
        """
        for tag in entry['__tags']:
            self.tag_file_mapping[tag].append((entry['year'], entry['ID']))
            self.tag_counts[tag] += 1

    def collect_authors_and_editors(self, entry):
        people = []
        target = None
        match entry:
            case {"__author": authors}:
                people = authors
                target = self.authors
            case {"__editor": editors}:
                people = editors
                target = self.editors
            case _:
                logging.warning("Unexpected entry: %s", entry['ID'])

        assert(bool(people))
        target.update(bib_utils.names_to_pairs(people, entry))

    def gen_years(self):
        """
        Report on bibliography year distributions of entries
        """
        years = [(int(x), f"{x:<8} : {y}") for x,y in self.year_counts.items()]
        return { "years" : "\n".join(x[1] for x in sorted(years, key=lambda x: x[0])) }

    def write_timelines(self):
        """
        Report timelines of tag uses
        """
        for tag, entries in self.tag_file_mapping.items():
            if len(entries) < min_tag_timeline:
                continue
            out_target     = self.locs.timelines / f"{tag}.tag_timeline"

            report = [f"---- Timeline of Tag: {tag} ----"]
            last_year = None
            for year, ent_id in sorted(entries, key=lambda x: x[0]):
                if last_year != year:
                    report.append(f"\n---------- {year} ----------")
                last_year = year
                report.append(f"{ent_id}")

            out_target.write_text("\n".join(report))
