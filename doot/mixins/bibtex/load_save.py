#!/usr/bin/env python3
"""

"""

##-- imports
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

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import bibtexparser as b
import doot
from .writer import JGBibTexWriter
from doot.utils.formats import latex
from bibtexparser.bparser import BibTexParser

__all__ = ["BibLoadSaveMixin"]

NEWLINE_RE     : Final = re.compile(r"\n+\s*")
default_convert_exclusions = ["file", "url", "ID", "ENTRYTYPE", "_FROM_CROSSREF", "doi", "crossref", "tags", "look_in", "note", "reference_number", "see_also"]
convert_exclusions = doot.config.on_fail(default_convert_exclusions, list).bibtex.convert_exclusions()

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
        """ Parse all the bibtext files into a shared database """
        try:
            def transform(entry):
                entry = self._entry_to_unicode(entry)
                if fn:
                    return fn(entry)
                return entry

            db                   = db or b.bibdatabase.BibDatabase()
            db.strings           = OverrideDict()
            bparser              = self._make_parser(transform)
            bparser.bib_database = db

            for x in files:
                logging.info("Loading bibtex: %s", x)
                text = pl.Path(x).read_bytes().decode("utf-8", "replace")
                bparser.parse(text, partial=True)
            logging.info("Bibtex loaded: %s entries", len(db.entries))
            return db
        except UnicodeDecodeError as err:
            raise Exception(f"Unicode Error in File: {x}, Start: {err.start}") from err
        except Exception as err:
            raise err.__class__(f"Bibtex File Loading Error: {x}", *err.args) from err

    def bc_db_to_str(self, db, lib_root:pl.Path, fn:None|callable=None) -> str:
        writer = JGBibTexWriter()
        fn = fn or self.bc_prepare_entry_for_write
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
                case _ if any([x in field for x in convert_exclusions]):
                    pass
                case "__tags":
                    delete_fields.add(field)
                    entry["tags"] = self._join_tags(entry[field])
                case "__paths" if bool(entry['__paths']):
                    delete_fields.add(field)
                    entry.update(self._path_strs(entry[field], lib_root))
                case "__author" | "__editor" if bool(entry[field]):
                    delete_fields.add(field)
                    entry[field.replace("__","")] = self._flatten_names(entry[field])
                case _ if "__" in field:
                    delete_fields.add(field)
                case _:
                    try:
                        entry[field] = latex.to_latex(entry[field])
                    except AttributeError as err:
                        raise AttributeError(f"Failed converting {field} to unicode: {entry}", *err.args) from err

        for field in delete_fields:
            if field == 'author' or field == "year":
                continue
            del entry[field]


    def _entry_to_unicode(self, entry):
        """
        convert the entry to unicode, removing newlines
        """
        for k,v in entry.items():
            if 'url' in k or 'file' in k:
                continue
            entry[k] = NEWLINE_RE.sub(" ", latex.to_unicode(v))
        entry['__as_unicode'] = True
        return entry

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

        final = " and ".join(result)
        return final


    def _join_tags(self, tagset) -> str:
        if not bool(tagset):
            return "__untagged"
        return ",".join(sorted(tagset))

    def _path_strs(self, pathdict, lib_root) -> dict:
        results = {}
        for field, path in pathdict.items():
            if not path.resolve().is_relative_to(lib_root):
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
        bparser.homogenise_fields         = False
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
