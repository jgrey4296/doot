#!/usr/bin/env python
"""
utilities for cleaning bibtex files
"""
##-- imports
from __future__ import annotations

import argparse
import logging as logmod
import pathlib as pl
from typing import Final
from dataclasses import InitVar, dataclass, field
from hashlib import sha256
from itertools import cycle
from math import ceil
from shutil import copyfile, move
from uuid import uuid4

import regex as re
from bibtexparser.latexenc import latex_to_unicode
from bkmkorg.bibtex.writer import JGBibTexWriter

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

__all__ = ["BibFieldCleanMixin", "BibPathCleanMixin"]

from bibtexparser import customization as bib_customization
from bibtexparser.latexenc import string_to_latex

STEM_CLEAN_RE : Final = re.compile(r"[^a-zA-Z0-9_]+")
UNDERSCORE_RE : Final = re.compile(r"_+")
NEWLINE_RE    : Final = re.compile(r"\n+\s*")
AND_RE        : Final = re.compile(r"\ and\ ", flags=re.IGNORECASE)
TAGSPLIT_RE   : Final = re.compile(r",|;")
TITLESPLIT_RE : Final = re.compile(r"^(.+?): (.+)$")

empty_match : Final = re.match("","")

class _PrivateCleanMixin:
    """
    Private Mixin utility methods
    """

    def _clean_parent_paths(self, entry, base_name, lib_root) -> list[tuple[str, pl.Path]]:
        """ prepare parent directories if they have commas in them
        handles clean target already existing
        """
        if 'crossref' in entry:
            return
        assert('__paths' in entry)
        assert('__base_name' in entry)
        base = entry['__base_name']

        results = []
        for field, fpath in entry['__paths'].items():
            match self.__ideal_parent(fpath, year, base):
                case None:
                    pass
                case _ as val:
                    results.append((field, val))

        return results

    def __ideal_parent(self, fpath, year, base, lib_root):
        """
        Get the correct parent location for files
        """
        #(focus: /lib/root/1922/bib_customization) (rst: blah.pdf)
        focus   = fpath.parent

        if not focus.is_relative_to(lib_root):
            # Not in library
            return None

        # Copy root for in place editing
        cleaned = pl.Path(lib_root)

        # Everything is in root/year/base
        cleaned /= year
        cleaned /= base

        return cleaned

    def _separate_names(self, text):
        names = bib_customization.getnames([x.strip() for x in AND_RE.split(text)])
        return [bib_customization.splitname(x.strip(), False) for x in names]

class BibFieldCleanMixin(_PrivateCleanMixin):
    """
    mixin for cleaning fields of bibtex records
    """

    def bc_match_year(self, entry, target, msg=None) -> None|tuple[str, str]:
        """
        check the year is the right one for the file its in
        """
        if entry['year'] == target:
            return None

        return entry['ID'], msg.format(target=target, actual=entry['year'])

    def bc_check_files(self, entry, msg) -> list[tuple[str, str]]:
        """
        check all files exist
        """
        assert('__paths' in entry)
        results = []
        for field, fpath in entry['__paths']:
            if pl.Path(entry[field]).exists():
                continue

            results.append((entry['ID'], msg.format(file=entry[field])))

        return results

    def bc_title_split(self, entry):
        if 'title' not in entry:
            return entry
        match (TAGSPLIT_RE.match(entry['title']) or empty_match).groups():
            case ():
                pass
            case (title, subtitle):
                entry['__orig_title'] = entry['title']
                entry['title']        = title
                entry['subtitle']     = subtitle

        return entry

    def bc_to_unicode(self, entry):
        """
        convert the entry to unicode, removing newlines
        """
        entry = bib_customization.convert_to_unicode(entry)
        entry.update({k:NEWLINE_RE.sub(" ", v) for k,v in entry.items()})
        entry['__as_unicode'] = True

    def bc_split_names(self, entry):
        """
        convert names to component parts, for authors and editors
        """
        try:
            match entry:
                case { "author": author }:
                    entry['__authors'] = self._separate_names(author)
                    entry['__split_names'] = "author"
                case { "editor" : editor }:
                    entry['__editors'] = self._separate_names(editor)
                    entry['__split_names'] = "editor"
                case _:
                    raise Exception("No author or editor", entry)
        except Exception as err:
            logging.warning("Error processing %s : %s", entry['ID'], err)

    def bc_tag_split(self, entry):
        """
        split raw tag strings into parts, clean and strip whitespace,
        then make them a set
        """
        tags = set()
        if "tags"          in entry and isinstance(entry["tags"], str):
            tags_subbed = NEWLINE_RE.sub("_", entry["tags"])
            tags.update(TAGSPLIT_RE.split(tags_subbed))
        if "keywords"      in entry and isinstance(entry["keywords"], str):
            tags_subbed = NEWLINE_RE.sub("_", entry["keywords"])
            tags.update(TAGSPLIT_RE.split(tags_subbed))
            del entry["keywords"]
        if "mendeley-tags" in entry and isinstance(entry["mendeley-tags"], str):
            tags_subbed = NEWLINE_RE.sub("_", entry["mendeley-tags"])
            tags.update(TAGSPLIT_RE.split(tags_subbed))
            del entry["mendeley-tags"]

        entry["__tags"] = {x.strip() for x in tags}
        return entry

class BibPathCleanMixin(_PrivateCleanMixin):
    """
    Mixin for cleaning path elements of bib records
    """

    def bc_expand_paths(self, entry, lib_root):
        if 'crossref' in entry:
            return

        results = set()
        for field, fname in entry.items():
            if 'file' not in field:
                continue
            assert(field not in results)
            if fname[0] not in  ["~", "/"]:
                fname = lib_root / fname
            fpath = pl.Path(fname).expanduser().resolve()
            results[field] = fpath

        entry['__paths'] = results

    def bc_base_name(self, entry) -> str:
        """
        Get the first author or editor's surname
        """
        assert("__split_names" in entry)
        assert("__as_unicode" in entry)
        target = None
        match entry:
            case { "__authors" : [author, *_] }:
                target = author['last'][0]
            case { "__editors" : [editor, *_] }:
                target = editor['last'][0]
            case _:
                raise Exception("No author or editor for entry: %s", entry)

        as_unicode = latex_to_unicode(target)
        as_ascii   = as_unicode.encode("ascii", "ignore").decode().replace("\\", "")
        entry['__base_name'] = as_ascii

    def bc_ideal_stem(self, entry) -> str:
        """
        create an ideal stem for an entry's files
        if there are multiple files, they will have a unique hex value added to their stem later
        """
        assert('__base_name' in entry)
        match entry:
            case { "title" : t }:
                title = t[:40]
            case { "short_parties": t }:
                title = t

        year      = entry['year']
        base_name = entry['__base_name']

        form       = f"{base_name}_{year}_{title}"
        # Convert latex characters to unicode
        as_unicode = latex_to_unicode(form)
        # Then flatten to ascii
        as_ascii   = as_unicode.encode("ascii", "ignore").decode()
        # Remove symbols
        clean      = STEM_CLEAN_RE.sub("_", as_ascii)
        # And collapse multiple underscores
        collapsed  = UNDERSCORE_RE.sub("_", clean)
        entry['__ideal_stem'] = collapsed.strip()

    def bc_prepare_file_movements(self, entry, lib_root) -> list:
        """
        Calculate the proper place for files
        """
        assert('__paths' in entry)
        assert('__base_name' in entry)
        assert('__ideal_stem' in entry)
        parents = self._clean_parent_paths(entry, LIB_ROOT)
        stem = entry['__ideal_stem']

        results = []
        for field, parent in parents:
            results.append((field,
                            entry['__paths'][field],
                            parent,
                            stem))

        return results

    def bc_unique_stem(self, orig, proposed) -> None|pl.Path:
        """
        Returns a guaranteed non-existing path, or None
        """
        assert(orig.exists())
        if orig.samefile(proposed):
            return None

        if orig.stem[:-6] == ideal_fp.stem:
            # fp is already a stem+uuid, so do nothing
            return proposed.parent / orig.name

        hexed  = proposed
        while hexed.exists():
            hex_val     = str(uuid4().hex)[:5]
            ideal_stem += f"_{hex_val}"
            hexed       = proposed.with_stem(ideal_stem)

        return hexed

def basic_clean(entry):
    """
    basic transforms from bibtexparser
    """
    bib_customization.type(entry)
    bib_customization.author(entry)
    bib_customization.editor(entry)
    bib_customization.journal(entry)
    bib_customization.keyword(entry)
    bib_customization.link(entry)
    bib_customization.doi(entry)

    return entry

def year_parse(entry):
    """
    parse the year into a datetime
    """
    if 'year' not in entry:
        year_temp = "2020"
    else:
        year_temp = entry['year']

    if "/" in year_temp:
        year_temp = year_temp.split("/")[0]

    year = datetime.datetime.strptime(year_temp, "%Y")
    entry['__year'] = year
