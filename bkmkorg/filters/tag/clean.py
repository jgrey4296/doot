#!/usr/bin/env python
"""
Script to Process Bibtex, bookmark, and org files for tags
and to clean them
"""
import argparse
import logging as root_logger
from math import ceil
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

import bibtexparser as b
import regex as re
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bkmkorg.utils.bibtex import entry_processors as bib_proc
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.tag import clean
from bkmkorg.utils.tag.collection import SubstitutionFile

logging = root_logger.getLogger(__name__)
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join(["Extracts all tags in all bibtex, bookmark and org files in specified dirs"]))
parser.add_argument('-t', '--target',action="append")
parser.add_argument('-c', '--cleaned', action="append")

bparser = BibTexParser(common_strings=False)
bparser.ignore_nonstandard_types = False
bparser.homogenise_fields = True

#--------------------------------------------------
def main():
    args = parser.parse_args()

    logging.info("---------- STARTING Tag Clean")
    logging.info("Targeting: {}".format(args.target))
    logging.info("Cleaning based on: {}".format(args.cleaned))

    #Load Cleaned Tags
    cleaned_tags  = SubstitutionFile.builder(args.cleaned)
    logging.info("Loaded {} tag substitutions".format(len(cleaned_tags)))

    #Load Bibtexs, html, orgs and clean each
    bibs, htmls, orgs, bkmks = retrieval.collect_files(args.target)
    clean.clean_bib_files(bibs   , cleaned_tags)
    clean.clean_org_files(orgs   , cleaned_tags)
    clean.clean_bkmk_files(bkmks , cleaned_tags)
    logging.info("Complete --------------------")


if __name__ == "__main__":
    main()
