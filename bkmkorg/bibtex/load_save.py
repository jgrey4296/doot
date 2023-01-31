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
from .writer import JGBibTexWriter

__all__ = ["BibLoadSaveMixin"]

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

    def bc_load_db(self, files:list[pl.Path], fn:callable=None, db=None) -> BibtexDatabase:
        return self._parse_bib_files(files, fn=fn, db=db)

    def bc_db_to_str(self, db, fn:callable, lib_root) -> str:
        writer = JGBibTexWriter()
        for entry in db.entries:
            fn(entry, lib_root)

        return writer.write(self.current_db)

    def bc_prepare_entry_for_write(self, entry, lib_root) -> None:
        """ convert processed __{field}'s into strings in {field},
        removing the the __{field} once processed
        """

        delete_fields = set()
        for field in entry.keys():
            if field[:2] != "__":
                continue

            delete_fields.add(field)
            match field:
                case "__tags":
                    entry["tags"] = self._join_tags(entry[field])
                case "__paths" if bool(entry['__paths']):
                    entry.update(self._path_strs(entry[field], lib_root))
                case "__authors":
                    pass
                case "__editors":
                    pass
                case _:
                    pass

        for field in delete_fields:
            del entry[field]

    def _join_tags(self, tagset) -> str:
        return ",".join(tagset)

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
        bparser.ignore_nonstandard_types = False
        bparser.homogenise_fields        = True
        bparser.customization            = func
        bparser.expect_multiple_parse     = True
        return bparser

    def _parse_bib_files(self, bib_files:list[pl.Path], fn=None, db=None):
        """ Parse all the bibtext files into a shared database """
        bparser = self._make_parser(fn)
        if db is None:
            logging.info("Creating new database")
            db = b.bibdatabase.BibDatabase()

        db.strings = OverrideDict()

        bparser.bib_database = db
        for x in bib_files:
            with open(x, 'r') as f:
                logging.info("Loading bibtex: %s", x)
                bparser.parse_file(f, partial=True)
        logging.info("Bibtex loaded: %s entries", len(db.entries))
        return db
