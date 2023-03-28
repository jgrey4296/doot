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

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
logmod.getLogger('bibtexparser').setLevel(logmod.CRITICAL)
##-- end logging

import shutil

import itertools
import doot
from doot.mixins.bibtex import clean as bib_clean
from doot.mixins.bibtex import utils as bib_utils
from doot.mixins.bibtex.load_save import BibLoadSaveMixin
from doot.utils.formats.timelinefile import TimelineFile
from doot import globber, tasker
from doot.mixins.commander import CommanderMixin
from doot.mixins.batch import BatchMixin
from doot.mixins.delayed import DelayedMixin
from doot.mixins.filer import FilerMixin
from doot.mixins.targeted import TargetedMixin
from doot.tasker import DootTasker
from doot.tasks.files.backup import BackupTask

pl_expand : Final = lambda x: pl.Path(x).expanduser().resolve()

min_tag_timeline : Final = doot.config.on_fail(10, int).bibtex.min_timeline()
stub_exts        : Final = doot.config.on_fail([".pdf", ".epub", ".djvu", ".ps"], list).bibtex.stub_exts()
clean_in_place   : Final = doot.config.on_fail(False, bool).bibtex.clean_in_place()

ENT_const        : Final = 'ENTRYTYPE'

class LibDirClean(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, FilerMixin):
    """
    Clean the directories of the bibtex library
    """

    def __init__(self, name="pdflibrary::clean", locs=None, roots=None, rec=True, exts=None):
        super().__init__(name, locs, roots or [locs.pdfs], rec=False, exts=exts)

    def set_params(self):
        return self.target_params()

    def filter(self, fpath):
        if fpath.is_dir() and not bool(list(fpath.iterdir())):
            return self.globc.keep
        return self.globc.discard

    def subtask_detail(self, task, fpath):
        task.update({
            "actions": [ (self.rmdirs, [fpath]) ],
        })

class BibtexClean(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, bib_clean.BibFieldCleanMixin, bib_clean.BibPathCleanMixin, BibLoadSaveMixin, BatchMixin, FilerMixin):
    """
    (src -> src) Clean all bib files
    formatting, fixing paths, etc
    """
    wrong_year_msg = " : Wrong Year: (Bibfile: {target}) != ({actual} : Entry)"
    bad_file_msg   = " : File Does Not Exist : {file}"

    def __init__(self, name="bibtex::clean", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.bibtex], exts=[".bib"], rec=rec)
        self.current_db   = None
        self.current_year = None
        self.issues       = []
        self.locs.ensure("build", "temp", "bibtex", "pdfs")

    def filter(self, fpath):
        if fpath.is_dir():
            return self.control.discard
        return self.control.accept

    def set_params(self):
        return [
            { "name": "move-files", "long": "move-files", "type": bool, "default": False },
            { "name": "clean-in-place", "short": "i", "type": bool, "default": clean_in_place},
        ] + self.target_params()

    def task_detail(self, task):
        issue_report = self.locs.build / "bib_clean_issues.report"
        task.update({
            "actions" : [
                lambda: { "key_max" : max((len(x[0]) for x in self.issues), default=1) },
                lambda task: { "issues" : "\n".join(f"{x[0]:<{task.values['key_max']}} {x[1]}" for x in self.issues) },
                (self.write_to, [issue_report, "issues"]),
                ],
            "targets" : [issue_report],
        })
        return task

    def subtask_detail(self, task, fpath):
        target = fpath if self.args['clean-in-place'] else self.locs.temp / fpath.name
        task.update({
            "actions" : [
                (self.load_and_clean, [fpath]), # -> cleaned
                self.db_to_str, # -> db
                (self.write_to, [target, "db"]),
            ],
        })
        return task

    def db_to_str(self):
        return {
            "db" : self.bc_db_to_str(self.current_db, self.bc_prepare_entry_for_write, self.locs.pdfs)
        }

    def load_and_clean(self, fpath):
        logging.info("Cleaning: %s", fpath)
        self.current_year = fpath.stem
        self.current_db   = self.bc_load_db([fpath], fn=self.on_parse_clean_entry)
        # Everything loaded, crossrefs resolved
        for entry in self.current_db.entries:
            self.loaded_clean_entry(entry)

    def on_parse_clean_entry(self, entry) -> dict:
        # Preprocess
        self.bc_to_unicode(entry)
        self.bc_lowercase_keys(entry)
        self.bc_tag_split(entry)
        assert("__tags" in entry)

        if 'year' not in entry:
            entry['year'] = "2023"

        if 'school' in entry and 'institution' not in entry:
            entry['institution'] = entry['school']
            del entry['school']

        if entry['ENTRYTYPE'].lower() in ["phdthesis", "mastersthesis"]:
            entry['type'] = entry['ENTRYTYPE'].lower().replace("thesis","")
            entry['ENTRYTYPE'] = "thesis"

        # TODO store entry, add it to correct year
        match self.bc_match_year(entry, self.current_year, self.wrong_year_msg):
            case (e_id, msg) as err:
                print(e_id + msg, file=sys.stderr)
                self.issues.append(err)

        self.bc_expand_paths(entry, self.locs.pdfs)
        assert("__paths" in entry)
        for e_id, msg in self.bc_check_files(entry, self.bad_file_msg):
            self.issues.append((e_id, msg))
            logging.warning(e_id + msg)

        return entry

    def loaded_clean_entry(self, entry) -> None:
        assert('crossref' not in entry or '_FROM_CROSSREF' in entry), entry
        self.bc_split_names(entry)
        self.bc_title_split(entry)
        self.bc_base_name(entry)
        self.bc_ideal_stem(entry)

        ##-- file path cleanup
        # Clean files [(field, orig, newloc, newstem)]
        movements : list[tuple[str, pl.Path, pl.Path, str]] = self.bc_prepare_file_movements(entry, self.locs.pdfs)
        orig_parents = set()
        for field, orig, new_dir, new_stem in movements:
            orig_parents.add(orig.parent)
            unique = self.bc_unique_stem(orig, (new_dir / new_stem).with_suffix(orig.suffix))
            if unique is None:
                continue

            if self.args['move-files'] and not new_dir.exists():
                new_dir.mkdir(parents=True)
            elif not new_dir.exists():
                logging.info("Proposed Directory Creation: %s", new_dir)

            if self.args['move-files']:
                entry['__paths'][field] = orig.rename(unique)
            else:
                logging.info("Proposed File Move: %s -> %s", orig, unique)
        ##-- end file path cleanup

        ##-- parent path cleanup
        for parent in orig_parents:
            try:
                should_rm = not bool(list(parent.iterdir()))
                # if should_rm and self.args['move-files']:
                #     parent.rmdir()
                if should_rm:
                    logging.info("Proposed Directory Cleanup: %s", parent)
            except OSError as err:
                if not err.args[0] == 66:
                    logging.exception("Removing empty directories went bad: ", err)
            ##-- end parent path cleanup

class BibtexReport(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, FilerMixin, BatchMixin, BibLoadSaveMixin, bib_clean.BibFieldCleanMixin, bib_clean.BibPathCleanMixin):
    """
    (src -> build) produce reports on the bibs found
    """

    def __init__(self, name="bibtex::report", locs=None, roots=None, rec=True):
        super().__init__(name, locs, roots or [locs.bibtex], rec=rec, exts=[".bib"])
        self.locs.update(timelines=self.locs.build / "timelines")
        self.locs.ensure("pdfs")

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
            self.bc_to_unicode(entry)
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
            case {"__authors": authors}:
                people = authors
                target = self.authors
            case {"__editors": editors}:
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

class BibtexStub(DelayedMixin, globber.DootEagerGlobber):
    """
    (src -> data) Create basic stubs for found pdfs and epubs
    """
    stub_t     = Template("@misc{stub_key_$id,\n  author = {},\n  title = {$title},\n  year = {$year},\n  file = {$file}\n}")

    def __init__(self, name="bibtex::stub", locs=None, roots=None, rec=False, exts=None):
        super().__init__(name, locs, roots or [locs.downloads, locs.desktop, locs.dropbox], rec=rec, exts=exts or stub_exts)
        self.source_file_set = set()
        self.max_stub_id      = 0
        self.stubs            = []

    def setup_detail(self, task):
        task.update({
            "actions": [
                self.read_stub_contents
            ]
        })
        return task

    def read_stub_contents(self):
        source_text = self.locs.bib_stub_file.read_text()
        file_re = re.compile(r"\s*file\s*=\s*{(.+)}")
        stub_re = re.compile(r"^@.+?{stub_key_(\d+),$")
        stub_ids = [0]
        for line in source_text.split("\n"):
            file_match = file_re.match(line)
            key_match  = stub_re.match(line)

            if key_match is not None:
                stub_ids.append(int(key_match[1]))

            if file_match is not None:
                self.source_file_set.add(pl.Path(file_match[1]).name)

        self.max_stub_id = max(stub_ids)
        logging.debug("Found %s existing stubs", len(self.source_file_set))

    def filter(self, fpath):
        if fpath.is_file() and fpath.name not in self.source_file_set:
            return self.globc.accept
        return self.globc.discard

    def task_detail(self, task):
        task.update({
            "actions" : [
                self.stub_all,
                self.append_stubs
            ],
        })
        return task

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [
                (self.move_to_workdir, [fpath]), # locs.src/fpath -> moved_to: locs.data/fpath
            ],
        })
        return task

    def move_to_workdir(self, fpath):
        src = fpath
        dst = self.locs.bibtex_working / fpath.name
        if dst.exists():
            src.rename(src.with_stem(f"exists_{src.stem}"))
            return None

        shutil.move(str(src), str(dst))
        # src.rename(dst)
        return { "moved_to" : str(dst)}

    def stub_all(self):
        wd = self.locs.bibtex_working
        for fpath in itertools.chain(wd.glob("*.pdf"), wd.glob("*.epub")):
            if fpath.name in self.source_file_set:
                continue

            self.max_stub_id += 1
            stub_str = BibtexStub.stub_t.substitute(id=self.max_stub_id,
                                                    title=fpath.stem,
                                                    year=datetime.datetime.now().year,
                                                    file=str(fpath.expanduser().resolve()))
            self.stubs.append(stub_str)

    def append_stubs(self):
        if not bool(self.stubs):
            return

        print(f"Adding {len(self.stubs)} stubs")
        with open(self.locs.bib_stub_file, 'a') as f:
            f.write("\n")
            f.write("\n\n".join(self.stubs))

class TODOBibtexWaybacker(DelayedMixin, TargetedMixin, globber.DootEagerGlobber):
    """
    get all urls from bibtexs,
    then check they are in wayback machine,
    or add them to it
    then add the wayback urls to the relevant bibtex entry
    """
    pass

class TODOPdfLibSummary(doot.DootTasker):
    """
    Compile the first n pages of each pdf in a decade together
    """
    pass

class TODOPdfBibtexCompile(doot.DootTasker):
    """
    Compile individual bibtex files into pdfs
    then combine them together into decades and total
    """
    pass

class TODOTimelineCompile(doot.DootTasker):
    """
    take a timeline and create a pdf of the citations,
    and the combined pdfs
    """
    pass

class TODOHashVerify(doot.DootTasker):
    """
    Check a random selection of files for hash consistency
    """
    pass
