#!/usr/bin/env python
"""
Script to clean a bibtex file, converting everything to unicode
"""
##-- imports
import argparse
import logging as root_logger
import pathlib as pl
from hashlib import sha256
from math import ceil
from shutil import copyfile, move
from uuid import uuid4

import bibtexparser as b
import regex as re
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.bibtex.writer import JGBibTexWriter
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.file.hash_check import file_to_hash
from bkmkorg.filters.bibtex.meta_data import check_pdf, add_metadata

##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(LOGLEVEL)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
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
##-- end argparse

NEWLINE_RE    = re.compile(r"\n+\s*")
STEM_CLEAN_RE = re.compile(r", *|\.+|-+")

def remove_newlines(record):
    for key in record:
        val         = record[key]
        record[key] = NEWLINE_RE.sub(" ", val)

def check_files(record):
    file_fields = [x for x in record.keys() if 'file' in x]
    for field in file_fields:
        orig_fp     = pl.Path(record[field])
        if record[field][0] not in  "~/":
            fp = LIB_ROOT / record[field]
        else:
            fp = orig_fp.expanduser().resolve()

        orig_parent = orig_fp.parent
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
    file_fields = [x for x in record.keys() if 'file' in x]
    for field in file_fields:
        orig_fp     = pl.Path(record[field])
        if record[field][0] not in  "~/":
            fp = LIB_ROOT / record[field]
        else:
            fp = orig_fp.expanduser().resolve()

        orig_parent = orig_fp.parent

        # assert(orig_parent.parent.name == record['year'])

        if "," not in fp.parent.name:
            continue

        logging.debug("Comma in: %s", fp.parent.name)
        cleaned   = fp.parent.name.split(",")[0].strip()
        fp_parent = fp.parent.with_name(cleaned)
        fp_clean  = fp_parent / fp.name
        if (not fp_parent.exists()) and fp.parent.exists():
            # rename the entire directory
            logging.debug("Renaming %s to %s", fp.parent, fp_parent)
            fp.parent.rename(fp_parent)
        elif (not fp_clean.exists()) and fp.exists():
            # Move just one file to correct dir
            fp = fp.rename(fp_clean)
        elif fp_clean.exists() and fp.exists():
            alt_stem = fp.stem + "_alt"
            fp_clean = fp_clean.with_stem(alt_stem)
            fp.rename(fp_clean)

        if orig_parent.exists() and not bool(list(orig_parent.iterdir())):
            # Remove original dir if its empty
            logging.debug("Original Dir is empty, removing: %s", orig_parent)
            orig_parent.rmdir()

        assert(fp_clean.exists())
        fp = fp_clean


        record[field] = str(fp)

    return record

def clean_stems(record):
    """
    Clean the stems of filenames, regularizing them
    Handles if theres already a file with the canonical name
    """
    file_fields = [x for x in record.keys() if 'file' in x]
    for field in file_fields:
        orig_fp     = pl.Path(record[field])
        if record[field][0] not in  "~/":
            fp = LIB_ROOT / record[field]
        else:
            fp = orig_fp.expanduser().resolve()

        orig_parent = orig_fp.parent

        assert(fp.exists())
        logging.debug("Cleaning stem")
        alt = "_alt" if "_alt" in fp.stem else ""
        title = STEM_CLEAN_RE.sub("_", record['title'][:40])
        year  = record['year']
        if "author" in record:
            base_name = c.splitname(record['author'].split("and")[0])['last'][0]
        elif 'editor' in record:
            base_name = c.splitname(record['author'].split("and")[0])['last'][0]
        else:
            raise Exception("No author or editor for record: %s", record)

        ideal_stem = f"{base_name}_{year}_{title}{alt}"
        ideal_fp   = fp.with_stem(ideal_stem)
        if ideal_stem == fp.stem:
            pass
        elif ideal_fp.exists():
            logging.warning("Ideal Stem Already Exists")
            hex_val    = str(uuid4().hex)[:5]
            ideal_stem += f"_{hex_val}"
            ideal_fp   = fp.with_stem(ideal_stem)
            assert(not ideal_fp.exists())
            fp         = fp.rename(ideal_fp)
        else:
            fp = fp.rename(ideal_fp)

        record[field] = str(fp)

    return record

def relativize_paths(record):
    """
    Convert file paths to relative
    """
    file_fields = [x for x in record.keys() if 'file' in x]
    for field in file_fields:
        orig_fp     = pl.Path(record[field])
        if record[field][0] not in  "~/":
            fp = LIB_ROOT / record[field]
        else:
            fp = orig_fp.expanduser().resolve()

        orig_parent = orig_fp.parent

        if fp.is_relative_to(LIB_ROOT):
            # write updated, relative to lib root
            logging.debug("Relativizing: %s", fp)
            relative_fp = fp.relative_to(LIB_ROOT)
            logging.debug("Relativized: %s", relative_fp)
            record[field] = str(relative_fp)

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
            orig_fp     = pl.Path(record[field])
            if record[field][0] not in  "~/":
                fp = LIB_ROOT / record[field]
            else:
                fp = orig_fp.expanduser().resolve()

            orig_parent = orig_fp.parent

            if fp.suffix == ".pdf" and fp.exists():
                entry_as_str : str = writer._entry_to_bibtex(entry)
                add_metadata(fp, record, entry_as_str)

def custom_clean(record):
    assert('year' in record)
    clean_tags(record)
    remove_newlines(record)
    clean_parent_paths(record)
    clean_stems(record)
    relativize_paths(record)
    check_files(record)

    return record


def main():
    args = parser.parse_args()
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
