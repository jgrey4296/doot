"""
Script to combine multiple bibtex files into one
"""
##-- imports
from __future__ import annotations

import argparse
import logging as root_logger
import pathlib as pl
from math import ceil

import bibtexparser as b
import regex as re
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bkmkorg.utils.bibtex import entry_processors as bib_proc
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
##-- end imports

# Setup
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##-- end logging

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog="""Integrates a collection of bibtex files into a single file. Targets can be flat directories""")
parser.add_argument('-t', '--target', action="append", required=True)
parser.add_argument('-o', '--output', default="./output/integrated.bib")
##-- end argparse

def main():
    args        = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()

    logging.info("Targeting: %s", args.target)
    logging.info("Output to: %s", args.output)

    #load each of the specified files
    target_files = retrieval.get_data_files(args.target, ".bib")
    dbs          = [BU.parse_bib_files(x, bib_proc.nop) for x in target_files]
    main_db      = b.bibdatabase.BibDatabase()
    # Load the main database
    if exists(args.output):
        BU.parse_bib_files(args.output, bib_proc.nop, database=main_db)

    main_set          = set(main_db.get_entry_dict().keys())
    total_entries     = main_db.entries[:]
    missing_keys_main = set()

    # Get entries missing from the main database
    for db in dbs:
        db_dict      = db.get_entry_dict()
        db_set       = set(db_dict.keys())
        missing_keys = db_set.difference(main_set)
        missing_keys_main.update(missing_keys)
        total_entries += [db_dict[x] for x in missing_keys]

    logging.info("%s missing entries", len(total_entries))
    main_db.entries = total_entries

    # Write out the combined database
    logging.info("Bibtex loaded")
    writer = BibTexWriter()
    writer.align_values = True
    with open(args.output,'a') as f:
        f.write(writer.write(main_db))

if __name__ == "__main__":
    main()
