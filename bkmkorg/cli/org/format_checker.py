"""
Script to read org files and check them for erroneous tags
"""
##-- imports
from __future__ import annotations
import argparse
import logging as root_logger
from math import ceil

import pathlib as pl
import bibtexparser as b
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
from bkmkorg.bibtex import parsing as BU
from bkmkorg.org.extraction import get_permalinks
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
                                epilog="\n".join(["Report org files with incorrect meta data of tweets"]))
parser.add_argument('-t', '--target', action="append", required=True)
parser.add_argument('-o', '--output', default="collected")
##-- end argparse

def main():
    logging.info("Org Check start: --------------------")
    args = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()
    args.target = [pl.Path(x).expanduser().resolve() for x in args.target]

    logging.info("Targeting: %s", args.target)
    logging.info("Output to: %s", args.output)

    found         = collect.collect_files(args.target)
    suspect_files = get_permalinks(found['.org'])

    logging.info("Found %s suspect files", len(suspect_files))
    with open(args.output,'w') as f:
        for id_str in suspect_files:
            f.write("{}\n".format(id_str))

    logging.info("Complete --------------------")


##-- ifmain
if __name__ == "__main__":
    main()
##-- end ifmain
