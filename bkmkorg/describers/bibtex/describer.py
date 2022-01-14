#!/usr/bin/env python
"""
Script to process bibtex file
Giving stats, non-tagged entries,
year distributions
firstnames, surnames.
"""
import argparse
import logging as root_logger
from math import ceil
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from collections import defaultdict

import bibtexparser as b
import regex as re
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser

from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.bibtex import entry_processors as bib_proc
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.diagram import make_bar
from bkmkorg.utils.tag.collection import TagFile

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

# Setup
console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog="\n".join(["Describe a bibtex file's:",
                                                    "Tags, year counts, authors,",
                                                    "And entries lacking files or with multiple files"]))
parser.add_argument('-t', '--target', default="~/github/writing/resources", help="Input target")
parser.add_argument('-o', '--output', default="bibtex",                     help="Output Target")
parser.add_argument('-f', '--files', action="store_true",                   help="Write to files")
parser.add_argument('-a', '--authors', action="store_true",                 help="Describe authors")
parser.add_argument('-y', '--years', action="store_true",                   help="Describe Years")


def process_db(db):

    proportion = int(len(db.entries) / 10)
    count = 0

    # Extracted data
    all_keys               = []
    all_years              = TagFile()
    author_counts          = TagFile()
    non_tagged             = []
    no_file                = []
    missing_files          = []

    # Enumerate over all entries, updated data
    for i, entry in enumerate(db.entries):
        # Log progress
        if i % proportion == 0:
            logging.info(f"{count}/10 Complete")
            count += 1

        if entry['ID'] in all_keys:
            logging.warning("Duplicate Key: {}".format(entry['ID']))

        all_keys.append(entry['ID'])
        # get tags
        e_tags = entry['tags']

        # get untagged
        if not bool(e_tags):
            non_tagged.append(entry)

        # count entries per year
        if 'year' in entry:
            all_years.inc(entry['year'])

        # count names
        for x in entry['p_authors']:
            for name in x:
                author_counts.inc(name)

        # Retrieve file information
        if not any(['file' in x for x in entry.keys()]):
            no_file.append(entry['ID'])

        else:
            filenames      = [y for x,y in entry.items() if 'file' in x]
            missing_files += [y for y in filenames if not exists(y)]

    return (all_keys,
            all_years,
            author_counts,
            non_tagged,
            no_file,
            missing_files)


def main():
    args = parser.parse_args()

    args.output = abspath(expanduser(args.output))
    assert(exists(args.target))

    logging.info("Targeting: {}".format(args.target))
    logging.info("Output to: {}".format(args.output))

    # Load targets
    bib_files = retrieval.get_data_files(args.target, ".bib")
    db = BU.parse_bib_files(bib_files, func=bib_proc.clean_full)
    logging.info("Bibtex loaded")

    logging.info(f"Processing Entries: {len(db.entries)}")
    result = process_db(db)
    logging.info("Processing complete")

    if args.years:
        with open("{}.years".format(args.output), 'w') as f:
            f.write(str(result[1]))


    # Build Author counts files
    if args.authors:
        with open("{}.authors".format(args.output), 'w') as f:
            f.write(str(result[2]))


    # Build Default Files
    if args.files:
        logging.info("Writing Descriptions of Files")
        with open(f"{args.output}.no_file", 'w') as f:
            f.write("\n".join(result[4]))

        with open(f"{args.output}.missing_file", 'w') as f:
            f.write("\n".join(result[5]))

    logging.info("Complete")


if __name__ == "__main__":
    main()
