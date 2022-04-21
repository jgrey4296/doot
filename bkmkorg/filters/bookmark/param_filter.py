"""
A simple trie usage bookmark processor
Pairs with bkmkorg/describers/bookmark_queries
"""
import argparse
import logging as root_logger
from os import listdir
from os.path import abspath, exists, expanduser, isfile, join, split, splitext

import regex as re
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.collections.trie import Trie
from bkmkorg.utils.bookmarks.collection import BookmarkCollection

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
parser.add_argument('-s', '--source', action="append", required=True)
parser.add_argument('-q', '--query', default=None)
parser.add_argument('-o', '--output', required=True)


query_re = re.compile(r'\*+\s+\(\d+\) (.+)$')

if __name__ == "__main__":
    args = parser.parse_args()
    args.output = abspath(expanduser(args.output))
    if args.query is not None:
        args.query = abspath(expanduser(args.query))

    #load any sources
    source_files = retrieval.get_data_files(args.source, ".bookmarks")
    total = BookmarkCollection()
    for bkmk_f in source_files:
        with open(bkmk_f, 'r') as f:
            total.add_file(f)

    #filter any queries
    if args.query:
        with open(args.query, 'r') as f:
            lines = f.readlines()
        matches = [query_re.findall(x) for x in lines]
        queries = set([x[0] for x in matches if x])
        # TODO total.filter_queries(queries)

    #export
    with open(args.output, "w") as f:
        f.write(str(total))
