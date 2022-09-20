#!/usr/bin/env python
"""
Script to clean a bibtex file, converting everything to unicode
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
from bkmkorg.filters.bibtex.meta_data import add_metadata, check_pdf
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.bibtex.writer import JGBibTexWriter
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.file.hash_check import file_to_hash

##-- end imports

##-- logging
LOGLEVEL = logmod.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
logmod.basicConfig(filename=LOG_FILE_NAME, level=logmod.INFO, filemode='w')

console = logmod.StreamHandler()
console.setLevel(LOGLEVEL)
logmod.getLogger('').addHandler(console)
logging = logmod.getLogger(__name__)
##-- end logging

LIB_ROOT = pl.Path("~/mega/pdflibrary").expanduser().resolve()

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=
                                 "\n".join(["Specify a Target bibtex file,",
                                            "Output file,",
                                            "Cleans entries,",
                                            "Records errors in an 'error' field for an entry."]),

                                 exit_on_error=True)

parser.add_argument('-t', '--target', action='append', required=True)
parser.add_argument('-o', '--output', default=None)
parser.add_argument('-m', '--metadata', action="store_true")
parser.add_argument('-v', '--verbose')
##-- end argparse

NEWLINE_RE        = re.compile(r"\n+\s*")
# STEM_CLEAN_RE     = re.compile(r", *|\.+|-+|:|\?|'|‘|’|@|\\|/|\(|\)|")
STEM_CLEAN_RE     = re.compile(r"[^a-zA-Z0-9_]+")
UNDERSCORE_RE     = re.compile(r"_+")

# TODO queue up and execute instructions after all changes have been calculated

def make_path(text):
    if text[0] not in  "~/":
        return LIB_ROOT / text

    return pl.Path(text).expanduser().resolve()

def short_path(path):
    if not path.is_relative_to(LIB_ROOT):
        return path

    return path.relative_to(LIB_ROOT)

def get_entry_base_name(record):
    """
    Get the first author or editor's surname
    """
    if "author" in record:
        authors   = record['author'].split("and")[0]
        base_name = c.splitname(authors)['last'][0]
    elif 'editor' in record:
        editors   = record['editor'].split("and")[0]
        base_name = c.splitname(editors)['last'][0]
    else:
        raise Exception("No author or editor for record: %s", record)

    as_unicode = latex_to_unicode(base_name)
    as_ascii   = as_unicode.encode("ascii", "ignore").decode()
    return as_ascii

def idealize_stem(record):
    title      = record['title'][:40]
    year       = record['year']
    base_name  = get_entry_base_name(record)

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

def remove_newlines(record):
    for key in record:
        val         = record[key]
        record[key] = NEWLINE_RE.sub(" ", val)

def check_files(record):
    file_fields = [x for x in record.keys() if 'file' in x]
    for field in file_fields:
        fp          = make_path(record[field])

        if fp.suffix == ".pdf":
            check_pdf(fp)


##-- tag cleaning
def clean_tags(record):
    try:
        tags = set()
        for field in ["tags", "keywords", "mendeley-tags"]:
            if field not in record:
                continue

            tags.update([x.strip() for x in record[field].split(",")])
            del record[field]

        record['tags'] = ",".join(sorted(tags))

    except Exception as e:
        logging.warning("Tag Error: %s", record['ID'])

##-- end tag cleaning

##-- path cleaning
def clean_parent_paths(record):
    """ Rename parent directories if they have commas in them
    handles clean target already existing
    """
    if 'crossref' in record:
        return

    file_fields = [x for x in record.keys() if 'file' in x]
    for field in file_fields:
        fp          = make_path(record[field])
        orig_parent = fp.parent

        base_name = get_entry_base_name(record)

        if fp.is_relative_to(LIB_ROOT) and 'year' in record:
            # Ensure the year directory is correct as well
            year          = record['year']
            parent_target = fp.parent.parent / base_name
        else:
            continue

        file_target = parent_target / fp.name

        if not parent_target.exists():
            parent_target.mkdir()

        match fp.parent.exists(), fp.exists(), file_target.exists():
            case _, True, False:
                logging.info("Moving single file %s to %s", short_path(fp), short_path(file_target))
                fp.rename(file_target)
            case _, True, True if not fp.samefile(file_target):
                logging.info("File Conflict %s and %s", short_path(fp), short_path(file_target))
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

        if orig_parent.exists() and not bool(list(orig_parent.iterdir())):
            # Remove original dir if its empty
            logging.info("Original Dir is empty, removing: %s", orig_parent)
            orig_parent.rmdir()

        fp            = file_target
        record[field] = str(fp)

    return record

def clean_stems(record):
    """
    Clean the stems of filenames, regularizing them
    Handles if theres already a file with the canonical name
    """
    if 'crossref' in record:
        return

    file_fields = [x for x in record.keys() if 'file' in x]
    for field in file_fields:
        fp          = make_path(record[field])
        orig_parent = fp.parent

        logging.debug("Cleaning stem")
        ideal_stem = idealize_stem(record)
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

def relativize_paths(record):
    """
    Convert file paths to relative
    """
    file_fields = [x for x in record.keys() if 'file' in x]
    for field in file_fields:
        fp            = make_path(record[field])
        record[field] = str(short_path(fp))

    return record

##-- end path cleaning

def add_metadata_to_db(db):
    writer   = JGBibTexWriter()
    count = 0
    for i, entry in enumerate(db.entries):
        if i % 10 == 0:
            logging.info("%s/10 Complete", count)
            count += 1

        record = c.convert_to_unicode(entry)

        file_fields = [x for x in record.keys() if 'file' in x]
        for field in file_fields:
            fp          = make_path(record[field])
            orig_parent = fp.parent

            if fp.suffix == ".pdf" and fp.exists():
                entry_as_str : str = writer._entry_to_bibtex(entry)
                add_metadata(fp, record, entry_as_str)

def custom_clean(record):
    assert('year' in record)
    clean_tags(record)
    remove_newlines(record)

    try:
        clean_parent_paths(record)
        clean_stems(record)
        relativize_paths(record)
        check_files(record)
    except Exception as err:
        logging.warning("Error Occurred for {}: {}".format(record, err))

    return record


def main():
    args = parser.parse_args()
    if args.verbose:
        logging.setLevel(logmod.DEBUG)

    args.target = [pl.Path(x).expanduser().resolve() for x in args.target]

    if args.output:
        args.output = pl.Path(args.output).expanduser().resolve()
        assert(args.output.is_file() or not args.output.exists())


    logging.info("---------- STARTING Bibtex Clean")
    logging.info("Targeting: %s", args.target)
    logging.info("Output to: %s", args.output)

    bib_files = retrieval.get_data_files(args.target, ".bib")
    db        = BU.parse_bib_files(bib_files, func=custom_clean)

    logging.info("Read %s entries", len(db.entries))

    # Write out the actual bibtex
    if args.output and bool(db.entries):
        logging.info("Writing out Cleaned Bibliography")
        writer = JGBibTexWriter()
        out_str = writer.write(db)
        with open(args.output,'w') as f:
            f.write(out_str)

    if args.metadata:
        add_metadata_to_db(db)


if __name__ == "__main__":
    main()
