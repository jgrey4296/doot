"""
Script to split a library into bib files based on tags
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
args = parser.parse_args()

args.target = abspath(expanduser(args.target))
args.output = abspath(expanduser(args.output))
assert(exists(args.target))

if not isdir(args.output):
    mkdir(args.output)


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
    record = c.keyword(record)
    # record = c.link(record)
    # record = c.doi(record)
    if "keywords" in record:
        record["keywords"] = [i.strip() for i in re.split(',|;', record["keywords"].replace('\n', ''))]
    if "mendeley-tags" in record:
        record["mendeley-tags"] = [i.strip() for i in re.split(',|;', record["mendeley-tags"].replace('\n', ''))]

    # record['p_authors'] = []
    # if 'author' in record:
    #     record['p_authors'] = [c.splitname(x, False) for x in record['author']]
    return record

parser.customization = custom

with open(args.target, 'r') as f:
    logging.info("Loading bibtex")
    db = b.load(f, parser)


#go through entries, creating a new db for each tag, and year, and author


logging.info("Bibtex loaded")
writer = BibTexWriter()
with open(args.output,'w') as f:
        f.write(writer.write(db))
