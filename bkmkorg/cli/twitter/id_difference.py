"""
Compare ids in library to ids in a file

"""
##-- imports
from __future__ import annotations

import pathlib as pl
import argparse
import logging as root_logger
from math import ceil

import bibtexparser as b
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
from bkmkorg.bibtex import parsing as BU
from bkmkorg.org.extraction import get_tweet_dates_and_ids

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
                                    epilog="\n".join(["Return ids missing from the library"]))
parser.add_argument('-t', '--library', action="append", required=True)
parser.add_argument('-t', '--target', action="append", required=True)
parser.add_argument('-o', '--output', default="collected")
##-- end argparse

def main():
    logging.info("Twitter ID Extractor start: --------------------")
    args         = parser.parse_args()
    args.output  = pl.Path(args.output).expanduser().resolve()
    args.library = [pl.Path(x).expanduser().resolve() for x in args.library]
    args.target  = [pl.Path(x).expanduser().resolve() for x in args.target]

    logging.info("Targeting: %s", args.target)
    logging.info("Library  : %s", args.library)
    logging.info("Output to: %s", args.output)

    found = collect.collect_files(args.library)
    tweet_details            = get_tweet_dates_and_ids(found['.org'])
    ids_set                  = {x[0] for x in tweet_details}

    # TODO Get ids from target text file
    # diff

    logging.info("Complete --------------------")



##-- ifmain
if __name__ == "__main__":
    main()
##-- end ifmain
