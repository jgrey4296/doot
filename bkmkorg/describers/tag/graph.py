#!/usr/bin/env python
"""
Script to Process Bibtex, bookmark, and org files for tags
and to collect them into a graph
"""
import argparse
import logging as root_logger
from math import ceil
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

import networkx as nx
import regex as re
from bibtexparser import customization as c

from bkmkorg.utils.bibtex import entry_processors as bib_proc
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.tag import graph as TR

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)

##############################
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join(["Extracts all tags in all bibtex, bookmark and org files in specified dirs"]))
parser.add_argument('-t', '--target',action="append")
parser.add_argument('-o', '--output', default="collected")



#--------------------------------------------------
def main():
    logging.info("---------- Tag Graphing")
    args = parser.parse_args()

    logging.info("Targeting: {}".format(args.target))
    logging.info("Output to: {}".format(args.output))

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
