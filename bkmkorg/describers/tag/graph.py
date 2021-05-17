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

import bibtexparser as b
import networkx as nx
import regex
import regex as re
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser

from bkmkorg.io.import.netscape import open_and_extract_bookmarks
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.file import retrieval

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
parser.add_argument('-o', '--output', default="collected")

bparser = BibTexParser(common_strings=False)
bparser.ignore_nonstandard_types = False
bparser.homogenise_fields = True

def custom(record):
    record = c.type(record)
    record = c.author(record)
    record = c.editor(record)
    record = c.journal(record)
    record = c.keyword(record)
    record = c.link(record)
    record = c.doi(record)
    tags = set()

    if 'tags' in record:
        tags.update([i.strip() for i in re.split(',|;', record["tags"].replace('\n', ''))])
    if "keywords" in record:
        tags.update([i.strip() for i in re.split(',|;', record["keywords"].replace('\n', ''))])
    if "mendeley-tags" in record:
        tags.update([i.strip() for i in re.split(',|;', record["mendeley-tags"].replace('\n', ''))])

    record['tags'] = tags
    record['p_authors'] = []
    if 'author' in record:
        record['p_authors'] = [c.splitname(x, False) for x in record['author']]
    return record


bparser.customization = custom

#--------------------------------------------------


if __name__ == "__main__":
    logging.info("Tag Graphing start: --------------------")
    args = parser.parse_args()
    args.output = abspath(expanduser(args.output))

    logging.info("Targeting: {}".format(args.target))
    logging.info("Output to: {}".format(args.output))

    bibs, htmls, orgs = retrieval.collect_files(args.target)
    bib_db = BU.parse_bib_files(bibs)

    main_graph = nx.Graph()

    TU.extract_tags_from_bibtex(bib_db, main_graph)
    TU.extract_tags_from_org_files(orgs, main_graph)
    TU.extract_tags_from_html_files(htmls, main_graph)

    nx.write_weighted_edgelist(main_graph, args.output)

    logging.info("Complete --------------------")
