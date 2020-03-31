"""
A Simpler trie usage bookmark processor
Pairs with bkmkorg/describers/bookmark_queries
"""
from bkmkorg.utils.trie import Trie
from bkmkorg.io.import_netscape import open_and_extract_bookmarks
from bkmkorg.io.export_netscape import exportBookmarks as html_exporter
from bkmkorg.io.export_org import exportBookmarks as org_exporter
from bkmkorg.io.export_plain import exportBookmarks as plain_exporter
from os.path import isfile,join,exists, expanduser, abspath
from os import listdir
import opener
import logging
import argparse
import regex as re

query_re = re.compile(r'\*+\s+\(\d+\) (.+)$')
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Load bookmarks",
                                                     "filtering a blacklist of URL parameters",
                                                     "Pairs with bkmkorg/describers/bookmark_queries"])
)
parser.add_argument('-s', '--source', action="append")
parser.add_argument('-q', '--query', default=None)
parser.add_argument('-o', '--output')

args = parser.parse_args()
args.source = [abspath(expanduser(x)) for x in args.source]
args.output = abspath(expanduser(args.output))
if args.query is not None:
    args.query = abspath(expanduser(args.query))

the_trie = Trie()
#load any sources
bkmk_sources = [open_and_extract_bookmarks(f) for f in args.source]

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
