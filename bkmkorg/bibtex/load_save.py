#!/usr/bin/env python3
"""

"""
##-- imports

##-- end imports

##-- default imports
from __future__ import annotations

import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end default imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import bibtexparser as b
import doot
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
from bibtexparser.latexenc import unicode_to_latex_map
from .writer import JGBibTexWriter

__all__ = ["BibLoadSaveMixin"]

default_escape = [' ', '{', '}']

def string_to_latex(string, escape_chars=None):
    """
    Convert a string to its latex equivalent
    modified slightly from the default in bibtexparser
    """
    if string.isascii():
        return string

    escape_chars = escape_chars or default_escape
    new = []
    for char in string:
        match char.isascii() or char in escape_chars:
            case True:
                new.append(char)
            case False:
                new.append(unicode_to_latex_map.get(char, char))

    return ''.join(new)

class OverrideDict(dict):
    """
    A Simple dict that doesn't error if a key isn't found.
    Used to avoid UndefinedString Exceptions in bibtex parsing
    """

    def __getitem__(self, k):
        if k not in self:
            logging.warning("Adding string to override dict: %s", k)
            self[k] = k
        return k

class BibLoadSaveMixin:

    def bc_load_db(self, files:list[str|pl.Path], fn:callable=None, db=None) -> BibtexDatabase:
        try:
            return self._parse_bib_files(files, fn=fn, db=db)
        except UnicodeDecodeError as err:
            raise Exception(f"File: {files}, Start: {err.start}") from err
        except Exception as err:
            raise err.__class__(f"File: {files}", *err.args) from err

    def bc_db_to_str(self, db, fn:callable, lib_root) -> str:
        writer = JGBibTexWriter()
        for entry in db.entries:
            fn(entry, lib_root)

        result = writer.write(self.current_db)
        return result

    def bc_prepare_entry_for_write(self, entry, lib_root) -> None:
        """ convert processed __{field}'s into strings in {field},
        removing the the __{field} once processed
        """

        delete_fields = set()
        if "_FROM_CROSSREF" in entry:
            delete_fields.update(entry.get('_FROM_CROSSREF', []))
            delete_fields.add('_FROM_CROSSREF')

        for field in sorted(entry.keys()):
            match field:
                case "ID"  | "ENTRYTYPE" | "_FROM_CROSSREF" :
                    pass
                case _ if "url" in field:
                    pass
                case _ if "file" in field:
                    pass
                case "tags" | "series" | "doi" | "crossref" :
                    pass
                case "__tags":
                    delete_fields.add(field)
                    entry["tags"] = self._join_tags(entry[field])
                case "__paths" if bool(entry['__paths']):
                    delete_fields.add(field)
                    entry.update(self._path_strs(entry[field], lib_root))
                case "__authors" if bool(entry[field]):
                    delete_fields.add(field)
                    entry['author'] = self._flatten_names(entry['__authors'])
                case "__editors" if bool(entry[field]):
                    delete_fields.add(field)
                    entry['editor'] = self._flatten_names(entry['__editors'])
                case _ if "__" in field:
                    delete_fields.add(field)
                case _:
                    try:
                        entry[field] = string_to_latex(entry[field])
                    except AttributeError as err:
                        raise AttributeError(f"Failed using {field}", *err.args) from err

        for field in delete_fields:
            if field == 'author':
                continue
            del entry[field]

    def _flatten_names(self, names:list[dict]) -> str:
        """ join names to  {von} Last, {Jr,} First and... """
        result = []
        for person in names:
            if not bool(person):
                continue
            parts = []
            parts.append(" ".join(person['von']).strip())
            parts.append(" ".join(person['last']).strip() + ("," if bool(person['first']) else ""))
            if bool(person['jr']):
                parts.append(" ".join(person['jr']).strip() + ",")

            parts.append(" ".join(person['first']).strip())
            result.append(" ".join(parts).strip())

        return string_to_latex(" and ".join(result))


    def _join_tags(self, tagset) -> str:
        if not bool(tagset):
            return "__untagged"
        return ",".join(sorted(tagset))

    def _path_strs(self, pathdict, lib_root) -> dict:
        results = {}
        for field, path in pathdict.items():
            if not path.is_relative_to(lib_root):
                results[field] = str(path)
                continue

            assert(field not in results)
            rel_path = path.relative_to(lib_root)
            results[field] = str(rel_path)

        return results

    def _make_parser(self, func):
        bparser = BibTexParser(common_strings=False)
        bparser.customization             = func
        bparser.ignore_nonstandard_types  = False
        bparser.homogenise_fields         = True
        bparser.expect_multiple_parse     = True
        bparser.add_missing_from_crossref = True
        bparser.alt_dict = {
            'authors'  : u'author',
            'editors'  : u'editor',
            'urls'     : u'url',
            'link'     : u'url',
            'links'    : u'url',
            'subjects' : u'subject',
            'xref'     : u'crossref',
            "school"   : "institution",
        }
        return bparser

    def _parse_bib_files(self, bib_files:list[str|pl.Path], fn=None, db=None):
        """ Parse all the bibtext files into a shared database """
        bparser = self._make_parser(fn)
        if db is None:
            logging.info("Creating new database")
            db = b.bibdatabase.BibDatabase()

        db.strings = OverrideDict()

        bparser.bib_database = db
        for x in bib_files:
            logging.info("Loading bibtex: %s", x)
            text = pl.Path(x).read_bytes().decode("utf-8", "replace")
            bparser.parse(text, partial=True)
        logging.info("Bibtex loaded: %s entries", len(db.entries))
        return db
