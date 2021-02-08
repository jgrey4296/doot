"""
Extract Twitter ID's from org files

"""
import logging as root_logger
import argparse
from math import ceil
from os import listdir
from os.path import join, isfile, exists, isdir, splitext, expanduser, abspath, split
from bkmkorg.io.import_netscape import open_and_extract_bookmarks
import regex as re
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
import bibtexparser as b
import regex

from bkmkorg.utils import retrieval
from bkmkorg.utils import bibtex as BU

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)

#--------------------------------------------------


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="\n".join(["Extracts all tweet ids in all org files in specified dirs"]))
    parser.add_argument('-t', '--target',action="append")
    parser.add_argument('-o', '--output', default="collected")

    logging.info("Twitter ID Extractor start: --------------------")
    args = parser.parse_args()
    args.output = abspath(expanduser(args.output))

    logging.info("Targeting: {}".format(args.target))
    logging.info("Output to: {}".format(args.output))

    bibs, htmls, orgs = retrieval.collect_files(args.target)
    ids_set = retrieval.extract_ids_from_orgs(orgs)

    logging.info("Found {} unique twitter ids".format(len(ids_set)))
    with open(args.output,'w') as f:
        for id_str in ids_set:
            f.write("{}\n".format(id_str))

    logging.info("Complete --------------------")
