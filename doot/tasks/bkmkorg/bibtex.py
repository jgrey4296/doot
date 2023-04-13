#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import datetime
import itertools
import logging as logmod
import pathlib as pl
import re
import shutil
import sys
import time
from collections import defaultdict
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from os.path import commonpath
from re import Pattern
from string import Template
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
logmod.getLogger('bibtexparser').setLevel(logmod.CRITICAL)
##-- end logging

min_tag_timeline     : Final[int] = doot.config.on_fail(10, int).bibtex.min_timeline()
stub_exts            : Final[list] = doot.config.on_fail([".pdf", ".epub", ".djvu", ".ps"], list).bibtex.stub_exts()
clean_in_place       : Final[bool] = doot.config.on_fail(False, bool).bibtex.clean_in_place()
wayback_wait         : Final[int] = doot.config.on_fail(10, int).bibtex.wayback_wait()
acceptible_responses : Final[list] = doot.config.on_fail(["200"], list).bibtex.accept_wayback()
ENT_const            : Final[str] = 'ENTRYTYPE'

class LibDirClean(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, FilerMixin):
    """
    Clean the directories of the bibtex library
    """

    def __init__(self, name="pdflib::clean", locs=None, roots=None, rec=True, exts=None):
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
        self.locs.ensure("build", "temp", "bibtex", "pdfs", task=name)

    def filter(self, fpath):
        if fpath.is_dir():
            return self.control.discard
        return self.control.accept

    @property
    def clean_in_place(self):
        return self.args['clean-in-place'] or self.args['move-files']

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
        target = fpath if self.clean_in_place else self.locs.temp / fpath.name
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
            "db" : self.bc_db_to_str(self.current_db, self.locs.pdfs)
        }

    def load_and_clean(self, fpath):
        logging.info("Cleaning: %s", fpath)
        self.current_year = fpath.stem
        self.current_db   = self.bc_load_db([fpath], fn=self.on_parse_check_entry)
        # Everything loaded, crossrefs resolved
        for entry in self.current_db.entries:
            self.loaded_clean_entry(entry)

    def on_parse_check_entry(self, entry) -> dict:
        # Preprocess
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
                logging.info("+ dir? : %s", new_dir)

            if self.args['move-files']:
                entry['__paths'][field] = orig.rename(unique)
            else:
                common = commonpath((orig, unique))
                logging.info("--- ")
                logging.info("|-  : %s", str(orig).removeprefix(common))
                logging.info("->  : %s", str(unique).removeprefix(common))
                logging.info("---")
        ##-- end file path cleanup

        ##-- parent path cleanup
        for parent in orig_parents:
            if not bool(list(parent.iterdir())):
                logging.info("Proposed Directory Cleanup: %s", parent)
            ##-- end parent path cleanup

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
            if "_refiled" in fpath.name:
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

        logging.info(f"Adding {len(self.stubs)} stubs")
        with open(self.locs.bib_stub_file, 'a') as f:
            f.write("\n")
            f.write("\n\n".join(self.stubs))

class BibtexWaybacker(DelayedMixin, TargetedMixin, globber.DootEagerGlobber, bib_clean.BibFieldCleanMixin, bib_clean.BibPathCleanMixin, BibLoadSaveMixin, BatchMixin, FilerMixin, WebMixin):
    """
    get all urls from bibtexs,
    then check they are in wayback machine,
    or add them to it
    then add the wayback urls to the relevant bibtex entry
    """

    def __init__(self, name="bibtex::wayback", locs=None, roots=None, exts=None):
        super().__init__(name, locs, roots or [locs.bibtex], rec=True, exts=exts or [".bib"])
        self.current_db   = None
        self.current_year = None

    def set_params(self):
        return self.target_params()

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [
                (self.load_and_clean, [fpath]), # -> cleaned
                self.db_to_str, # -> db
                (self.write_to, [fpath, "db"]),
            ],
        })
        return task

    def db_to_str(self):
        return {
            "db" : self.bc_db_to_str(self.current_db, self.locs.pdfs)
        }

    def load_and_clean(self, fpath):
        logging.info("Cleaning: %s", fpath)
        self.current_year = fpath.stem
        self.current_db   = self.bc_load_db([fpath], fn=self.on_parse_check_entry)

    def on_parse_check_entry(self, entry) -> dict:
        url_keys = [k for k in entry.keys() if "url" in k]
        if not bool(url_keys):
            return entry

        save_prefix = "https://web.archive.org/save"
        for k in url_keys:
            url = entry[k]
            match self.check_wayback(url):
                case None: # is wayback url? continue
                    pass
                case False: # create wayback url and replace
                    result = self.post_url(save_prefix, url=url)
                    recheck = self.check_wayback(url)
                    if isinstance(recheck, str):
                        entry[k] = recheck
                case str() as way_url: # wayback url exists? replace
                    entry[k] = way_url
                case _:
                    raise TypeError("Unknown wayback response")

        return entry

    def check_wayback(self, url) -> bool|str:
        if "web.archive.org" in url:
            return None
        time.sleep(wayback_wait)
        check_url = " http://archive.org/wayback/available?url=" + url
        json_data : dict = self.get_url(check_url)
        if 'archived_snapshots' not in json_data:
            return False

        closest = json_data['archived_snapshots'].get('closest', None)
        if closest is not None and closest['status'] in acceptible_responses and closest.get('available', False):
            return closest["url"]

class BibtexCompile(DelayedMixin, TargetedMixin, globber.DootEagerGlobber):
    """
    Compile individual bibtex files into pdfs
    then combine them together into decades and total
    """

    def __init__(self, name="bibtex::compile", locs=None, roots=None, output=None):
        super().__init__(name, locs, roots or [locs.bibtex], rec=False, exts=[".bib"])
        self.output = output or locs.pdf_summary
        self.locs.ensure("temp", task=name)

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [
                # create tex wrapper in temp
                # compile bs
            ],
        })
        return task

class TimelineCompile(DelayedMixin, TargetedMixin, globber.DootEagerGlobber):
    """
    take a timeline and create a pdf of the citations,
    and the combined pdfs
    """

    def __init__(self, name="timeline::compile", locs=None, roots=None, exts=None, output=None):
        super().__init__(name, locs, roots or [locs.timelines], exts=exts or [".tag_timeline"])
        self.output = output or self.locs.build

    def set_params(self):
        return self.target_params()

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [
                # construct tex file
                # Compile
                     ],
        })
        return task

class TODOHashVerify(DelayedMixin, TargetedMixin, globber.DootEagerGlobber):
    """
    Check a random selection of files for hash consistency
    """

    def __init__(self, name="bibtex::hash.check", locs=None, roots=None, exts=None):
        super().__init__(name, locs, roots or [locs.bibtex], exts=exts or [".bib"])

    def set_params(self):
        return self.target_params()

    def subtask_detail(self, task, fpath):
        task.update({
            "actions" : [],
        })
        return task
