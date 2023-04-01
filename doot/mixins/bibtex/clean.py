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
from doot.mixins.bibtex.writer import JGBibTexWriter

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

__all__ = ["BibFieldCleanMixin", "BibPathCleanMixin"]

from bibtexparser import customization as bib_customization

STEM_CLEAN_RE  : Final = re.compile(r"[^a-zA-Z0-9_]+")
UNDERSCORE_RE  : Final = re.compile(r"_+")
NEWLINE_RE     : Final = re.compile(r"\n+\s*")
AND_RE         : Final = re.compile(r"\ and\ ", flags=re.IGNORECASE)
TAGSPLIT_RE    : Final = re.compile(r",|;")
TITLESPLIT_RE  : Final = re.compile(r"^\s*(.+?): (.+)$")
TITLE_CLEAN_RE : Final = re.compile("[^a-zA-Z0-9]")

empty_match : Final = re.match("","")

class BibFieldCleanMixin:
    """
    mixin for cleaning fields of bibtex records
    """

    def bc_lowercase_keys(self, entry):
        uppercase = {x for x in entry.keys() if not (x.islower() or x.isupper()) }
        entry.update({x.lower(): entry.pop(x) for x in uppercase})

    def bc_match_year(self, entry, target, msg=None) -> None|tuple[str, str]:
        """
        check the year is the right one for the file its in
        """
        if 'year' not in entry:
            raise KeyError(f"Entry doesn't have a year: {entry}")
        if entry['year'] == target:
            return None

        return entry['ID'], msg.format(target=target, actual=entry['year'])

    def bc_title_split(self, entry):
        if 'title' not in entry:
            return entry
        if "subtitle" in entry:
            return entry

        match (TITLESPLIT_RE.match(entry['title']) or empty_match).groups():
            case ():
                pass
            case (title, subtitle):
                entry['__orig_title'] = entry['title']
                entry['title']        = (title[0].upper() + title[1:]).strip()
                entry['subtitle']     = (subtitle[0].upper() + subtitle[1:]).strip()

        return entry

    def bc_split_names(self, entry):
        """
        convert names to component parts, for authors and editors
        """
        match entry:
            case { "author" : "" }:
                logging.warning("Entry Has empty author: %s", entry['ID'])
                entry['author']        = "Anon"
                entry['__author']     = self._separate_names("Anon")
                entry['__split_names'] = "author"
            case { "editor" : "" }:
                logging.warning("Entry Has empty editor: %s", entry['ID'])
                entry['editor']        = "Anon"
                entry['__editor']     = self._separate_names("Anon")
                entry['__split_names'] = "editor"
            case { "author": author }:
                entry['__author'] = self._separate_names(author)
                entry['__split_names'] = "author"
            case { "editor" : editor }:
                entry['__editor']     = self._separate_names(editor)
                entry['__split_names'] = "editor"
            case _:
                logging.warning("Entry Has No author or editor: %s", entry['ID'])
                entry['author']        = "Anon"
                entry['__author']     = self._separate_names("Anon")
                entry['__split_names'] = "author"

        return entry

    def bc_tag_split(self, entry):
        """
        split raw tag strings into parts, clean and strip whitespace,
        then make them a set
        """
        tags_subbed     = NEWLINE_RE.sub("_", entry.get("tags", ""))
        tags            = TAGSPLIT_RE.split(tags_subbed)
        entry["__tags"] = {x.strip() for x in tags if bool(x.strip())}
        if not bool(entry["__tags"]):
            entry["__tags"].add("__untagged")
        return entry

    def _separate_names(self, text):
        try:
            names = AND_RE.split(text)
            result = [bib_customization.splitname(x.strip(), False) for x in names]
            return result
        except StopIteration:
            raise IndexError(f"Unbalanced curlys in {text}")

class BibPathCleanMixin:
    """
    Mixin for cleaning path elements of bib records
    """

    def bc_expand_paths(self, entry, lib_root):
        if 'crossref' in entry:
            entry['__paths'] = {}
            return

        results = dict()
        for field, fname in entry.items():
            if 'file' not in field:
                continue
            assert(field not in results)
            if fname[0] not in  ["~", "/"]:
                fname = lib_root / fname
            fpath = pl.Path(fname).expanduser().resolve()
            results[field] = fpath

        entry['__paths'] = results

    def bc_check_files(self, entry, msg) -> list[tuple[str, str]]:
        """
        check all files exist
        """
        assert('__paths' in entry)
        results = []
        for field, fpath in entry['__paths'].items():
            if pl.Path(fpath).exists():
                continue

            results.append((entry['ID'], msg.format(file=fpath)))

        return results

    def bc_base_name(self, entry) -> str:
        """
        Get the first author or editor's surname
        """
        assert("__split_names" in entry)
        assert("__as_unicode" in entry)
        target = None
        try:
            match entry:
                case { "__author" : [author, *_] }:
                    target = author['last'][0]
                case { "__editor" : [editor, *_] }:
                        target = editor['last'][0]
                case _:
                    logging.warning("No author or editor for entry: %s", entry)
                    target = str(uuid4().hex)[:5]
        except IndexError as err:
            logging.error("Bad Acces to author/editor in %s", entry)
            raise err

        as_ascii = target.encode("ascii", "replace").decode().replace("?", "")
        entry['__base_name'] = TITLE_CLEAN_RE.sub("", as_ascii)

    def bc_ideal_stem(self, entry):
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
            case _:
                title = "_"
                logging.warning("Entry Missing Title: %s", entry)

        year        = entry['year']
        base_name   = entry['__base_name']
        title_ascii = title.encode("ascii", "replace").decode().replace("?", "")

        form       = f"{base_name}_{year}_{title_ascii}"
        # Remove symbols
        clean      = STEM_CLEAN_RE.sub("_", form)
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
        parents = self.__clean_parent_paths(entry, lib_root)
        stem    = entry['__ideal_stem']

        results = []
        for field, parent in parents:
            results.append((field,
                            entry['__paths'][field],
                            parent,
                            stem))

        return results

    def __clean_parent_paths(self, entry, lib_root) -> list[tuple[str, pl.Path]]:
        """ prepare parent directories if they have commas in them
        handles clean target already existing
        """
        assert('__paths' in entry)
        assert('__base_name' in entry)
        base = entry['__base_name']
        year = entry['year']
        results = []

        for field, fpath in entry['__paths'].items():
            if not fpath.exists():
                continue
            match self.__ideal_parent(fpath, year, base, lib_root):
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

    def bc_unique_stem(self, orig:pl.Path, proposed:pl.Path) -> None|pl.Path:
        """
        Returns a guaranteed non-existing path, or None
        """
        if not orig.exists() or (proposed.exists() and orig.samefile(proposed)):
            return None

        stems_eq   = orig.stem[:-6] == proposed.stem
        parents_eq = orig.parent == proposed.parent
        match parents_eq, stems_eq:
            case True, True:
                return None
            case False, True:
                return proposed.parent / orig.name
            case _:
                pass

        hexed  = proposed
        while hexed.exists():
            logging.debug("Finding a unique non-existent path")
            hex_val     = str(uuid4().hex)[:5]
            hexed       = proposed.with_stem(f"_{hex_val}")

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
