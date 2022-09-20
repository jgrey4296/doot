#!/usr/bin/env python
"""
Script to Process Bibtex, bookmark, and org files for tags
and to collect them into a graph
"""
##-- imports
from __future__ import annotations
import argparse
import logging as root_logger
from math import ceil

import pathlib as pl
import networkx as nx
import regex as re
from bibtexparser import customization as c

from bkmkorg.utils.bibtex import entry_processors as bib_proc
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.tag import graph as TR
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
                                 epilog="\n".join(["Extracts all tags in all bibtex, bookmark and org files in specified dirs"]))
parser.add_argument('-t', '--target', action="append", required=True)
parser.add_argument('-o', '--output', default="collected")
##-- end argparse


def main():
    logging.info("---------- Tag Graphing")
    args = parser.parse_args()

    logging.info("Targeting: %s", args.target)
    logging.info("Output to: %s", args.output)

    bibs, htmls, orgs, bkmks = retrieval.collect_files(args.target)
    bib_db                   = BU.parse_bib_files(bibs, func=bib_proc.tags)
    main_graph               = TR.TagGraph()

    main_graph.extract_bibtex(bib_db)
    main_graph.extract_org(orgs)
    main_graph.extract_bookmark(bkmks)

    main_graph.write(args.output)


    logging.info("Complete --------------------")


if __name__ == "__main__":
    main()
