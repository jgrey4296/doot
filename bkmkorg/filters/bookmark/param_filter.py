"""
A simple trie usage bookmark processor
Pairs with bkmkorg/describers/bookmark_queries
"""
import argparse
import logging as root_logger
from os import listdir
from os.path import abspath, exists, expanduser, isfile, join, split, splitext

import opener
import regex as re
from bkmkorg.io.reader.netscape import open_and_extract_bookmarks
from bkmkorg.io.writer.netscape import exportBookmarks as html_exporter
from bkmkorg.io.writer.org import exportBookmarks as org_exporter
from bkmkorg.io.writer.plain import exportBookmarks as plain_exporter
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.file import retrieval
from bkmkorg.utils.trie import Trie

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
# Setup
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Load bookmarks",
                                                        "filtering a blacklist of URL parameters",
                                                        "Pairs with bkmkorg/describers/bookmark_queries"])
)
parser.add_argument('-s', '--source', action="append")
parser.add_argument('-q', '--query', default=None)
parser.add_argument('-o', '--output')


query_re = re.compile(r'\*+\s+\(\d+\) (.+)$')

if __name__ == "__main__":
    args = parser.parse_args()
    args.output = abspath(expanduser(args.output))
    if args.query is not None:
        args.query = abspath(expanduser(args.query))

    the_trie = Trie()
    #load any sources
    source_files = retrieval.get_data_files(args.source, ".html")
    bkmk_sources = [y for x in source_files for x in open_and_extract_bookmarks(x)]

    #insert into the trie
    for bkmk_group in bkmk_sources:
        for bkmk in bkmk_group:
            the_trie.insert(bkmk)

    #filter any queries
    if args.query:
        with open(args.query, 'r') as f:
            lines = f.read().split('\n')
        matches = [query_re.findall(x) for x in lines]
        queries = set([x[0] for x in matches if x])
        the_trie.filter_queries(queries)

    #export
    bkmktuples = the_trie.get_tuple_list()
    html_exporter(bkmktuples, "{}.html".format(args.output))
    org_exporter(bkmktuples, "{}.org".format(args.output))
    plain_exporter(bkmktuples, "{}.txt".format(args.output))
