"""
Compare 2 bibtex files
"""


import IPython
import bibtexparser as b
from bibtexparser.bparser import BibTexParser
from bibtexparser import customization as c
from os.path import join, isfile, exists, isdir, splitext, expanduser, abspath
from os import listdir
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


parser = argparse.ArgumentParser("")
parser.add_argument('-t', '--target', action='append')
args = parser.parse_args()

args.target = [abspath(expanduser(x)) for x in args.target]

logging.info("Targeting: {}".format(args.target))

all_dbs = []
for t in args.target:
    parser = BibTexParser(common_strings=False)
    parser.ignore_nonstandard_types = False
    parser.homogenise_fields = True

    with open(t, 'r') as f:
        db = b.load(f, parser)
    all_dbs.append(db)

logging.info("DB Sizes: {}".format(", ".join([str(len(x.entries)) for x in all_dbs])))
