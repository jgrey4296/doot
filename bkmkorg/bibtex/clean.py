#!/usr/bin/env python
"""
utilities for cleaning bibtex files
"""
##-- imports
import argparse
import logging as logmod
import pathlib as pl
from dataclasses import InitVar, dataclass, field
from hashlib import sha256
from math import ceil
from shutil import copyfile, move
from uuid import uuid4

import bibtexparser as b
import regex as re
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
from bibtexparser.latexenc import latex_to_unicode
from bkmkorg.bibtex.meta_data import add_metadata, check_pdf
from bkmkorg.bibtex import parsing as BU
from bkmkorg.bibtex.writer import JGBibTexWriter
from bkmkorg.files.hash_check import file_to_hash

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

STEM_CLEAN_RE     = re.compile(r"[^a-zA-Z0-9_]+")
UNDERSCORE_RE     = re.compile(r"_+")

##-- path util
def full_path(text, lib_root):
    if text[0] not in  ["~", "/"]:
        return lib_root / text

    return pl.Path(text).expanduser().resolve()

def short_path(path, lib_root):
    if not path.is_relative_to(lib_root):
        return path

    return path.relative_to(lib_root)

def expand_paths(record, lib_root):
    for field in [x for x in record.keys() if 'file' in x]:
        fp            = full_path(record[field], lib_root)
        record[field] = str(fp)

    return record

def relativize_paths(record, lib_root):
    """
    Convert file paths to relative
    """
    for field in [x for x in record.keys() if 'file' in x]:
        fp            = full_path(record[field], lib_root)
        record[field] = str(short_path(fp, lib_root))

    return record

##-- end path util

def get_entry_base_name(record):
    """
    Get the first author or editor's surname
    """
    target = None
    match record:
        case { "__authors" : [author, *_] }:
            target = author['last'][0]
        case { "__editors" : [editor, *_] }:
            target = editor['last'][0]
        case _:
            raise Exception("No author or editor for record: %s", record)

    as_unicode = latex_to_unicode(target)
    as_ascii   = as_unicode.encode("ascii", "ignore").decode().replace("\\", "")
    return as_ascii

def idealize_stem(record, base_name):
    """
    create an ideal stem for a file, from a record
    """
    match record:
        case { "title" : t }:
            title = t[:40]
        case { "short_parties": t }:
            title = t

    year = record['year']

    form       = f"{base_name}_{year}_{title}"
    # Convert latex characters to unicode
    as_unicode = latex_to_unicode(form)
    # Then flatten to ascii
    as_ascii   = as_unicode.encode("ascii", "ignore").decode()
    # Remove symbols
    clean      = STEM_CLEAN_RE.sub("_", as_ascii)
    # And collapse multiple underscores
    collapsed  = UNDERSCORE_RE.sub("_", clean)
    return clean.strip()

def clean_parent_paths(record, base_name, lib_root):
    """ Rename parent directories if they have commas in them
    handles clean target already existing
    """
    if 'crossref' in record:
        return

    for field in [x for x in record.keys() if 'file' in x]:
        fp          = pl.Path(record[field])
        orig_parent = fp.parent

        if fp.is_relative_to(lib_root) and 'year' in record:
            # Ensure the year directory is correct as well
            year          = record['year']
            parent_target = fp.parent.parent / base_name

        file_target = parent_target / fp.name

        if not parent_target.exists():
            parent_target.mkdir()

        match fp.parent.exists(), fp.exists(), file_target.exists():
            case _, True, False:
                logging.info("Moving single file %s to %s", short_path(fp, lib_root), short_path(file_target, lib_root))
                fp.rename(file_target)
            case _, True, True if not fp.samefile(file_target):
                logging.info("File Conflict %s and %s", short_path(fp, lib_root), short_path(file_target, lib_root))
                alt_stem    = file_target.stem + "_alt"
                file_target = file_target.with_stem(alt_stem)
                fp.rename(file_target)
            case _, True, True:
                # they are the same file, so no problem
                pass
            case False, False, True:
                # File has been moved by an whole directory move
                pass
            case _, _, _, _:
                raise Exception("Unexpected parent path situation", (fp, file_target))


        fp            = file_target
        record[field] = str(fp)

    return record

def clean_stems(record, ideal_stem, lib_root):
    """
    Clean the stems of filenames, regularizing them
    Handles if theres already a file with the canonical name
    """
    if 'crossref' in record:
        return

    for field in [x for x in record.keys() if 'file' in x]:
        fp          = full_path(record[field], lib_root)
        orig_parent = fp.parent

        logging.debug("Cleaning stem")
        ideal_fp   = fp.with_stem(ideal_stem)
        match fp.exists(), ideal_fp.exists():
            case False, True:
                fp = ideal_fp
            case True, True if not fp.samefile(ideal_fp) and fp.stem[:-6] == ideal_fp.stem:
                # fp is already a stem+uuid, so do nothing
                pass
            case True, True if not fp.samefile(ideal_fp):
                logging.warning("Ideal Stem Already Exists: %s", ideal_fp)
                hex_val    = str(uuid4().hex)[:5]
                ideal_stem += f"_{hex_val}"
                ideal_fp   = fp.with_stem(ideal_stem)
                assert(not ideal_fp.exists())
                fp         = fp.rename(ideal_fp)
            case True, False:
                logging.info("Renaming %s to %s", fp, ideal_fp)
                fp = fp.rename(ideal_fp)

        record[field] = str(fp)

    return record
