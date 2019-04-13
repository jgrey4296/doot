"""
Script to filter tags, and substitute other tags
"""
import IPython
import bibtexparser as b
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser import customization as c
from os.path import join, isfile, exists, isdir, splitext, expanduser, abspath
from os import listdir, mkdir
import regex as re
from math import ceil
import argparse
# Setup root_logger:
from os.path import splitext, split
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################

#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser("")
parser.add_argument('-t', '--target', default="~/Mega/library.bib")
parser.add_argument('-o', '--output', default="bibtex")
parser.add_argument('-f', '--filter')
parser.add_argument('-s', '--sub')
args = parser.parse_args()

args.target = abspath(expanduser(args.target))
args.output = abspath(expanduser(args.output))
if args.filter:
    args.filter = abspath(expanduser(args.filter))
if args.sub:
    args.sub = abspath(expanduser(args.sub))
assert(exists(args.target))

logging.info("Targeting: {}".format(args.target))
logging.info("Output to: {}".format(args.output))

parser = BibTexParser(common_strings=False)
parser.ignore_nonstandard_types = False
parser.homogenise_fields = True

def custom(record):
    # record = c.type(record)
    # record = c.author(record)
    # record = c.editor(record)
    # record = c.journal(record)
    # record = c.link(record)
    # record = c.doi(record)
    record['tags'] = set([i.strip() for i in re.split(',|;', record['tags'].replace('\n',''))])

    # record['p_authors'] = []
    # if 'author' in record:
    #     record['p_authors'] = [c.splitname(x, False) for x in record['author']]
    return record

parser.customization = custom

with open(args.target, 'r') as f:
    logging.info("Loading bibtex")
    db = b.load(f, parser)

# Get the filter terms
filter = set()
if args.filter and exists(args.filter):
    logging.info("Loading filter")
    with open(args.filter, 'r') as f:
        lines = f.read().split('\n')
    filter = set([x.strip() for x in lines])

# get the substitute tags
sub = {}
subset = set()
if args.sub and exists(args.sub):
    logging.info("Loading Sub")
    with open(args.sub, 'r') as f:
        lines = f.read().split('\n')
    sub = { x.strip() : y.strip() for a in lines for x,y in a.split(':')}
    subset = set(list(sub.keys()))

# Perform the filtering and substituting
logging.info("Performing filter and sub")
for ent in db.entries:
    ent['tags'].difference_update(filter)
    inter = ent['tags'].intersection(subset)
    ent['tags'].difference_update(inter)
    ent['tags'].update([subset[x] for x in inter])
    ent['tags'] = ",".join(ent['tags'])


logging.info("Writing")
writer = BibTexWriter()
with open("{}.bib".format(args.output),'w') as f:
        f.write(writer.write(db))
