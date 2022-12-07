#!/usr/bin/env python
"""
Compare 2+ bibtex files, output number of entries missing from the largest bibtex

"""

##-- imports
import argparse
import logging as root_logger
import pathlib as pl
import bibtexparser as b
from bibtexparser.bparser import BibTexParser

from bkmkorg.bibtex import parsing as BU
from bkmkorg.files import collect

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

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog="\n".join(["Compare bibtex files, print out the keys missing from the first"]))
parser.add_argument('-t', '--target', action='append', help="Target Bibtex (repeatable)", required=True)


def main():
    args        = parser.parse_args()
    args.target = [pl.Path(x).expanduser().resolve() for x in args.target]

    logging.info("Targeting: %s", args.target)

    # Get Bibtex files
    all_bib_paths = collect.get_data_files(args.targeet, ".bib")
    all_dbs = []
    for t in all_bib_paths:
        # Use a new bib_parser for each so library isn't shared
        bib_parser = BibTexParser(common_strings=False)
        bib_parser.ignore_nonstandard_types = False
        bib_parser.homogenise_fields = True

        with open(t, 'r') as f:
            db = b.load(f, bib_parser)
            all_dbs.append(db)

    logging.info("DB Sizes: %s", ", ".join([str(len(x.entries) for x in all_dbs])))

    # Sort the bibtex's by their size
    sorted_dbs = sorted([(len(x.entries), x) for x in all_dbs], reverse=True)

    # Use the largest as Primary
    head = sorted_dbs[0][1]
    rst = sorted_dbs[1:]
    head_set = {x['ID'] for x in head.entries}
    missing_keys = set([])

    # For remaining, get entries that are missing
    for _, db in rst:
        db_set = {x['ID'] for x in db.entries}
        if head_set.issuperset(db_set):
            continue

        missing_keys.update(db_set.difference(head_set))

    logging.info("%s Keys missing from master: %s", len(missing_keys), "\n".join(missing_keys))


##-- ifmain
if __name__ == "__main__":
    main()

##-- end ifmain
