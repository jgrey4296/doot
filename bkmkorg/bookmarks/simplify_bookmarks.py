"""
A Simpler trie usage bookmark processor
"""
from trie import Trie
from netscape_bookmark_exporter import exportBookmarks as html_exporter
from org_exporter import exportBookmarks as org_exporter
from plain_exporter import exportBookmarks as plain_exporter
from os.path import isfile,join,exists, expanduser, abspath
from os import listdir
import html_opener
import logging
import IPython
import argparse
import regex as re

query_re = re.compile(r'\*+\s+\(\d+\) (.+)$')

parser = argparse.ArgumentParser("")
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
bkmk_sources = [html_opener.open_and_extract_bookmarks(f) for f in args.source]

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
