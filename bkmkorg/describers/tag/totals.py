#!/usr/bin/env python
"""
Script to Process Bibtex, bookmark, and org files for tags
and to collect them
"""
import argparse
import logging as root_logger
import re
from os import mkdir
from os.path import abspath, expanduser, isdir, join, split, splitext, exists
import sys

from bibtexparser import customization as c
from bkmkorg.utils.bibtex import entry_processors as bib_proc
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.tag import clean
from bkmkorg.utils.tag.collection import SubstitutionFile, TagFile
from bkmkorg.utils.tag.graph import TagGraph

# Setup logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)

# Setup
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog="\n".join(["Extracts all tags in all bibtex, bookmark and org files in specified dirs"]))
parser.add_argument('-t', '--target',action="append", required=True)
parser.add_argument('-o', '--output', default="collected")
parser.add_argument('-c', '--cleaned', action="append", required=True)



def main():
    logging.info("---------- STARTING Tag Totals")
    cli_args = parser.parse_args()
    cli_args.output = abspath(expanduser(cli_args.output))

    logging.info("Targeting: {}".format(cli_args.target))
    if isdir(cli_args.output) and not exists(cli_args.output):
        mkdir(cli_args.output)
    if isdir(cli_args.output):
        cli_args.output = join(cli_args.output, "tags")
    logging.info("Output to: {}".format(cli_args.output))
    logging.info("Cleaned Tags locations: {}".format(cli_args.cleaned))

    bibs, htmls, orgs, bkmks = retrieval.collect_files(cli_args.target)
    bib_db    = BU.parse_bib_files(bibs, func=bib_proc.tags)
    tag_graph = TagGraph()

    bib_tags  = tag_graph.extract_bibtex(bib_db)
    org_tags  = tag_graph.extract_org(orgs)
    bkmk_tags = tag_graph.extract_bookmark(bkmks)

    with open(cli_args.output + "_bib.tags", 'w') as f:
        f.write(str(bib_tags))

    with open(cli_args.output + "_org.tags", 'w') as f:
        f.write(str(org_tags))

    with open(cli_args.output + "_bkmk.tags", 'w') as f:
        f.write(str(bkmk_tags))

    with open(cli_args.output + "_total.tags", 'w') as f:
        f.write(str(tag_graph))

    logging.info("Completed Total Count --------------------")

    if not bool(cli_args.cleaned):
        sys.exit()

    # load existing tag files
    cleaned       = SubstitutionFile.builder(cli_args.cleaned)

    # get new tags
    tags : TagFile      = tag_graph.tags
    new_tags : TagFile  = cleaned.difference(tags)

    # group them separately, alphabeticaly
    # To be included in the separate tag files
    with open(cli_args.output + "_new.tags", 'w') as f:
        f.write(str(new_tags))

    logging.info("Completed Uncleaned Count --------------------")

if __name__ == "__main__":
    main()
