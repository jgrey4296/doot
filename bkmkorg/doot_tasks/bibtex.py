#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import datetime
import logging as logmod
import pathlib as pl
import re
import sys
from collections import defaultdict
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from string import Template
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

import bkmkorg
import doot
from bkmkorg.bibtex import clean as bib_clean
from bkmkorg.bibtex import parsing as bib_parse
from bkmkorg.bibtex import writer as bib_write
from bkmkorg.file_formats.timelinefile import TimelineFile
from doot import globber
from doot.tasker import DootTasker

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
logmod.getLogger('bibtexparser').setLevel(logmod.CRITICAL)
##-- end logging

from bkmkorg.bibtex import entry_processors as entproc
from bibtexparser.latexenc import string_to_latex

stub_file        = doot.config.or_get("resources/todo.bib").tool.doot.bibtex.todo_file()
min_tag_timeline = doot.config.or_get(10).tool.doot.bibtex.min_timeline()
stub_exts        = doot.config.or_get([".pdf", ".epub"]).tool.doot.bibtex.stub_exts()
LIB_ROOT         = pl.Path(doot.config.or_get("~/pdflibrary").tool.doot.bibtex.lib_root()).expanduser().resolve()

clean_in_place   = doot.config.or_get(False).tool.doot.bibtex.clean_in_place()

ENT_const = 'ENTRYTYPE'

class LibDirClean(globber.DirGlobber):
    pass

class BibtexClean(globber.EagerFileGlobber):
    """
    (src -> src) Clean all bib files
    formatting, fixing paths, etc
    """

    def __init__(self, name="bibtex::clean", dirs=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], exts=[".bib"], rec=rec)
        self.current_db   = None
        self.current_year = None
        self.writer = bib_write.JGBibTexWriter()
        self.issues = []

    def task_detail(self, task):
        task.update({
            "name" : "report_issues",
            "actions" : [self.write_issues]
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [ (self.clean_bibtex_file, [fpath]), # -> cleaned
                          (self.write_cleaned, [fpath]),
                         ],
            "file_dep" : [ fpath ],
            "verbosity" : 2,
        })
        return task

    def clean_bibtex_file(self, fpath):
        self.current_year = fpath.stem
        # read
        self.current_db = bib_parse.parse_bib_files([fpath], func=self.clean_record)

        # back to string to write out
        for entry in self.current_db.entries:
            self.prepare_entry_for_write(entry)

        db_text = self.writer.write(self.current_db)
        logging.info("Bibtex db -> Text (%s, %s)", len(db_text), len(self.current_db.entries))
        return { 'cleaned' : db_text}

    def clean_record(self, record):
        try:
            # Preprocess
            record    = entproc.to_unicode(record)
            entry     = entproc.split_names(record)
            record    = bib_clean.expand_paths(record, LIB_ROOT)
            base_name = bib_clean.get_entry_base_name(record)
            ideal_stem = bib_clean.idealize_stem(record)

            self.check_year(record)
            self.check_files(record)
            # Main process
            record = entproc.tag_split(record)

            # Clean files
            # bib_clean.clean_parent_paths(record, LIB_ROOT)
            # bib_clean.clean_stems(record, ideal_stem, LIB_ROOT)

            return record
        except Exception as err:
            print(f"Error Occurred for {record['ID']}: {err}", file=sys.stderr)
            raise err

    def prepare_entry_for_write(self, entry):
        entry['tags'] = ",".join(entry['__tags'])
        bib_clean.relativize_paths(record, LIB_ROOT)
        for field in entry.keys():
            match (field[:2], field):
                case ("__", _):
                    pass
                case (_, 'ID'):
                    pass
                case (_, x) if "file" in x or "url" in x:
                    pass
                case _:
                    entry[field] = string_to_latex(entry[field])

    def clean_parents(self, entry):
        return

    def clean_stems(self, entry):
        return

    def relativize_paths(self, entry):
        return

    def check_year(self, entry):
        # TODO store record, add it to correct year
        if entry['year'] == self.current_year:
            return
        print(f"Wrong Year: Entry {entry['ID']} : {entry['year']} != {self.current_year}", file=sys.stderr)
        self.issues.append(f"Wrong Year: Entry {entry['ID']} : {entry['year']} != {self.current_year}")

    def check_files(self, entry):
        for field in [x for x in entry.keys() if 'file' in x]:
            if pl.Path(entry[field]).exists():
                continue

            print(f"{entry['ID']} : File Does Not Exist : {entry[field]}", file=sys.stderr)
            self.issues.append(f"{entry['ID']} : File Does Not Exist : {entry[field]}")

    def write_cleaned(self, fpath, task):
        logging.info("Writing out cleaned bibtex: (%s) %s", len(task.values['cleaned']), fpath)
        if clean_in_place:
            fpath.write_text(task.values['cleaned'])
        else:
            (self.dirs.temp / fpath.name).write_text(task.values['cleaned'])

    def write_issues(self):
        logging.info("Writing out %s issues", len(self.issues))
        (self.dirs.build / "clean_issues.report").write_text("\n".join(self.issues))

class BibtexReport(globber.EagerFileGlobber):
    """
    (src -> build) produce reports on the bibs found
    """

    def __init__(self, name="bibtex::report", dirs=None, roots=None, rec=True):
        super().__init__(name, dirs, roots or [dirs.src], rec=rec, exts=[".bib"])
        self.dirs.update(timelines=self.dirs.build / "timelines")

        self.db                             = bib_parse.parse_bib_files([])
        self.tag_file_mapping               = defaultdict(list)
        self.tag_counts                     = defaultdict(lambda: 0)
        self.year_counts                    = defaultdict(lambda: 0)
        self.type_counts                    = defaultdict(lambda: 0)
        self.files_counts                   = defaultdict(lambda: 0)
        self.authors : set[tuple[str, str]] = set()
        self.editors : set[tuple[str, str]] = set()

    def task_detail(self, task):
        task.update({
            "name" : "final",
            "actions" : [
                self.report_years,
                self.report_authors_and_editors,
                self.report_types,
                self.report_files,
                self.report_timelines,
            ],
            "targets" : [self.dirs.build / f"{x}.report" for x in ["years", "authors", "editors", "types", "files", "timelines"]],
            "clean" : True,
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [(self.read_file_into_db, [fpath])],
        })
        return task

    def read_file_into_db(self, fpath):
        bib_parse.parse_bib_files([fpath], database=self.db, func=self.process_entry)
        logging.info("Read file %s, total db entries: %s", fpath, len(self.db.entries))

    def process_entry(self, entry):
        try:
            entry = entproc.to_unicode(entry)
            entry = entproc.tag_split(entry)
            entry = entproc.split_names(entry)

            self.collect_tags(entry)
            self.collect_authors_and_editors(entry)
            self.year_counts[entry['year']] += 1
            self.type_counts[entry[ENT_const]] += 1

            if any("file" in key for key in entry.keys()):
                self.files_counts[entry[ENT_const]] += 1

        except Exception as err:
            logging.warning("Failure to process %s : %s", original['ID'], err)
        finally:
            return entry

    def collect_tags(self, entry):
        """
        Get all tags from all entries
        """
        tags = entry['tags']
        for tag in tags:
            self.tag_file_mapping[tag].append((entry['year'], entry['ID']))
            self.tag_counts[tag] += 1

    def collect_authors_and_editors(self, entry):
        people = []
        target = None
        match entry:
            case {"__authors": authors}:
                people = authors
                target = self.authors
            case {"__editors": editors}:
                people = editors
                target = self.editors
            case _:
                logging.warning("Unexpected entry: %s", entry['ID'])

        assert(bool(people))
        for person in people:
            parts = [" ".join(person[x]).strip() for x in ["first", "last", "von", "jr"]]
            match parts:
                case [only, "", "", ""] | ["", only, "", ""]:
                    logging.warning("Only a single name found in %s : %s", entry['ID'], person)
                    target.add((only, ""))
                case [first, last, "", ""]:
                    target.add((f"{last},", first))
                case [first, last, von, ""]:
                    target.add((f"{von} {last},", first))
                case [first, last, von, jr]:
                    target.add((f"{von} {last},", f"{jr}, {first}"))
                case _:
                    logging.warning("Unexpected item in bagging area: %s", parts)

    def report_years(self):
        """
        Report on bibliography year distributions of entries
        """
        target = self.dirs.build / "years.report"
        years = [(int(x), f"{x:<8} : {y}") for x,y in self.year_counts.items()]
        target.write_text("\n".join(x[1] for x in sorted(years, key=lambda x: x[0])))

    def report_authors_and_editors(self):
        """
        Report bibliography author distributions
        """
        author_target = self.dirs.build / "authors.report"
        author_max = max(len(x[0]) for x in self.authors)

        author_target.write_text("\n".join(sorted((f"{last:<{author_max}}{first}" for last,first in self.authors), key=lambda x: x[0].lower())))

        editor_target = self.dirs.build / "editors.report"
        editor_max = max(len(x[0]) for x in self.editors)
        editor_target.write_text("\n".join(sorted((f"{last:<{editor_max}}{first}" for last,first in self.editors), key=lambda x: x[0].lower())))

    def report_types(self):
        """
        Report entry type distributions (book, article, proceedings etc)
        """
        target = self.dirs.build / "types.report"
        target.write_text("\n".join(sorted(f"{x:<15} : {y}" for x,y in self.type_counts.items())))

    def report_files(self):
        """
        report file anomalys.
        """
        target = self.dirs.build / "files.report"

        target.write_text("\n".join(sorted(f"{x:<15} : {y}" for x,y in self.files_counts.items())))

    def report_timelines(self):
        """
        Report timelines of tag uses
        """
        for tag, entries in self.tag_file_mapping.items():
            if len(entries) < min_tag_timeline:
                continue
            out_target     = self.dirs.timelines / f"{tag}.tag_timeline"

            report = [f"---- Timeline of Tag: {tag} ----"]
            last_year = None
            for year, ent_id in sorted(entries, key=lambda x: x[0]):
                if last_year != year:
                    report.append(f"\n---------- {year} ----------")
                last_year = year
                report.append(f"{ent_id}")

            out_target.write_text("\n".join(report))

class BibtexStub(globber.EagerFileGlobber):
    """
    (src -> data) Create basic stubs for found pdfs and epubs
    """
    stub_t     = Template("@misc{stub_$id,\n  author = {},\n  title = {$title},\n  year = {$year},\n  file = {$file}\n}")

    def __init__(self, name="bibtex::stub", dirs=None, roots=None, rec=False, exts=None):
        super().__init__(name, dirs, roots or [dirs.src], rec=rec, exts=exts or stub_exts)
        self.source_text = pl.Path(stub_file).read_text()
        self.stubs       = []

    def filter(self, fpath):
        return fpath.name not in self.source_text

    def task_detail(self, task):
        task.update({
            "actions" : [self.append_stubs],
            })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [
                (self.move_file, fpath), # dirs.src/fpath -> moved_to: dirs.data/fpath
                (self.stub_entry, fpath), # moved_to
            ],
        })
        return task

    def move_file(self, fpath):
        src = fpath
        dst = self.dirs.src / fpath.name
        if dst.exists():
            src.rename(src.with_stem(f"exists_{src.stem}"))
            return None

        src.rename(dst)
        return { "moved_to" : str(dst)}

    def stub_entry(self, task):
        if 'moved_to' not in task.values:
            return

        fpath = pl.Path(task.values['moved_to'])
        stub_str = BibtexStub.stub_t.substitute(id=num,
                                                title=fpath.stem,
                                                year=datetime.datetime.now().year,
                                                file=str(fpath.expanduser().resolve()))
        self.stubs.append(stub_str)

    def append_stubs(self):
        with open(stub_file, 'a') as f:
            f.write("\n\n".join(self.stubs))
