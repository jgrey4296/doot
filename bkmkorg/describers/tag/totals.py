#!/usr/bin/env python
"""
Script to Process Bibtex, bookmark, and org files for tags
and to collect them
"""
##-- imports
from __future__ import annotations
import argparse
import logging as root_logger
import re
import sys

import pathlib as pl
from bibtexparser import customization as c
from bkmkorg.utils.bibtex import entry_processors as bib_proc
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.tag import clean
from bkmkorg.utils.tag.collection import SubstitutionFile, TagFile
from bkmkorg.utils.tag.graph import TagGraph
##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Pathlib(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)

##-- end logging

# Setup
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog="\n".join(["Extracts all tags in all bibtex, bookmark and org files in specified dirs"]))
parser.add_argument('-t', '--target',action="append", required=True)
parser.add_argument('-o', '--output', default="collected")
parser.add_argument('-c', '--cleaned', action="append", required=True)



def main():
    logging.info("---------- STARTING Tag Totals")
    cli_args = parser.parse_args()
    cli_args.output = pl.Path(cli_args.output).expanduser().resolve()

    logging.info("Targeting: {}".format(cli_args.target))
    if cli_args.output.is_dir() and not cli_args.output.exists():
        cli_args.output.mkdir()

    if cli_args.output.is_dir():
        cli_args.output = cli_args.output / "output.tags"

    logging.info("Output to: {}".format(cli_args.output))
    logging.info("Cleaned Tags locations: {}".format(cli_args.cleaned))

    bibs, htmls, orgs, bkmks = retrieval.collect_files(cli_args.target)
    bib_db    = BU.parse_bib_files(bibs, func=bib_proc.tags)
    tag_graph = TagGraph()

    bib_tags  = tag_graph.extract_bibtex(bib_db)
    org_tags  = tag_graph.extract_org(orgs)
    bkmk_tags = tag_graph.extract_bookmark(bkmks)

    for data, stem_name in zip((bib_tags, org_tags, bkmk_tags, tag_graph),
                               ("bib", "org", "bkmk", "graph")):

        with open(cli_args.output.with_stem(stem_name), 'w') as f:
            f.write(str(data))

    logging.info("Completed Total Count --------------------")

    if not bool(cli_args.cleaned):
        sys.exit()

    # load existing tag files
    cleaned       = SubstitutionFile.builder(cli_args.cleaned)

    # get new tags
    tags     : TagFile = tag_graph.tags
    new_tags : TagFile = cleaned.difference(tags)

    # group them separately, alphabeticaly
    # To be included in the separate tag files
    with open(cli_args.output.with_stem("new"), 'w') as f:
        f.write(str(new_tags))

    logging.info("Completed Uncleaned Count --------------------")

if __name__ == "__main__":
    main()
