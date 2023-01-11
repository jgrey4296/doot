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
from bkmkorg.bibtex.meta_data import add_metadata, check_pdf
from bkmkorg.bibtex import parsing as BU
from bkmkorg.bibtex.writer import JGBibTexWriter
from bkmkorg.files import collect
from bkmkorg.files.hash_check import file_to_hash
from bkmkorg.bibtex import clean

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

# TODO queue up and execute instructions after all changes have been calculated

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

    bib_files = collect.get_data_files(args.target, ".bib")
    db        = BU.parse_bib_files(bib_files, func=clean.custom_clean)

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


##-- ifmain
if __name__ == "__main__":
    main()

##-- end ifmain
