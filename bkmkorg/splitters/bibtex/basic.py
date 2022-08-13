##-- imports
from __future__ import annotations

import pathlib as pl
import argparse
from bkmkorg.utils.bibtex import entry_processors as bib_proc
import logging as root_logger
from math import ceil

import bibtexparser as b
import regex as re
from bibtexparser import customization as c
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
##-- end imports


##-- logging
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
                                    epilog="""Splits a bibtex file into multiple separate ones,
                                    by TAG, YEAR or AUTHOR,
                                    --output is a directory""")
parser.add_argument('-t', '--target', default="~/Mega/library.bib")
parser.add_argument('-o', '--output', default="tag_split")
parser.add_argument('-T', '--TAGS', action='store_true')
parser.add_argument('-Y', '--YEARS', action='store_true')
parser.add_argument('-A', '--AUTHORS', action='store_true')
##-- end argparse


if __name__ == "__main__":
    args        = parser.parse_args()
    args.target = pl.Path(args.target).expanduser().resolve()
    args.output = pl.Path(args.output).expanduser().resolve()

    assert(args.target.exists())
    assert(args.output.is_dir())
    if not args.output.exists():
        args.output.mkdir()

    logging.info("Targeting: %s", args.target)
    logging.info("Output to: %s", args.output)

    parser                          = BibTexParser(common_strings=False)
    parser.ignore_nonstandard_types = False
    parser.homogenise_fields        = True
    parser.customization            = bib_proc.nop

    # Load bibtex
    with open(args.target, 'r') as f:
        logging.info("Loading bibtex")
        db = b.load(f, parser)

    #go through entries, creating a new db for each tag, and year, and author
    db_dict = {}
    for entry in db.entries:
        if args.TAGS:
            tags = [i.strip() for i in re.split(',|;', entry["tags"].replace("\n",""))]
            for tag in tags:
                if tag not in db_dict:
                    db_dict[tag] = BibDatabase()
                db_dict[tag].entries.append(entry)
        if args.YEARS:
            if 'year' not in entry:
                raise Exception("Years specified, entry has no year: %s", entry['ID'])

            if entry['year'] not in db_dict:
                db_dict[entry['year']] = BibDatabase()
            db_dict[entry['year']].entries.append(entry)

        if args.AUTHORS:
            raise Exception("not implemented AUTHORS yet")

    # Write out split bibtex files
    logging.info("Writing Bibtex")
    writer = BibTexWriter()
    writer.align_values = True

    for k,v in db_dict.items():
        clean_name = k.replace("/","_")
        with open(args.output / f"{clean_name}.bib",'w') as f:
            f.write(writer.write(v))
