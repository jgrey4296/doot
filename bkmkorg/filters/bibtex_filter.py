"""
Script to filter tags, and substitute other tags
"""
import IPython
import bibtexparser as b
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser import customization as c
from os.path import join, isfile, exists, isdir
from os.path import split, splitext, expanduser, abspath
from os import listdir, mkdir
import regex as re
import argparse
# Setup root_logger:
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

#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join(["Filter tags out of a bibtex file",
                                                   "Then substitute tags for others",
                                                   "-f {file} newline separated list",
                                                   "-s {file} newline separated list of colon separated pairs"])
                                 )
parser.add_argument('-t', '--target', default="~/Mega/library.bib")
parser.add_argument('-o', '--output', default="bibtex")
parser.add_argument('-s', '--source', default=None)
args = parser.parse_args()

args.target = abspath(expanduser(args.target))
args.output = abspath(expanduser(args.output))
if args.source:
    args.source = abspath(expanduser(args.filter))
assert(exists(args.source))

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
    record['tags'] = {i.strip() for i in re.split(', |;', record['tags'].replace('\n', ''))}

    # record['p_authors'] = []
    # if 'author' in record:
    #     record['p_authors'] = [c.splitname(x, False) for x in record['author']]
    return record

parser.customization = custom

with open(args.target, 'r') as f:
    logging.info("Loading bibtex")
    db = b.load(f, parser)

# Get the filter terms
master_dict = {}
filter_set = set()
sub_set = set()

if args.source and exists(args.source):
    sources = [args.source]
    if isdir(args.source):
        sources = [x for x in listdir(args.source) if splitext(x)[1] == ".org"]
    for source_file in sources:
        logging.info("Loading Sources: {}".format(len(sources)))
        with open(args.source, 'r') as f:
            lines = f.read().split('\n')
        applicable_lines = [x for x in lines if x[0] != "*"]
        master_dict.update({x.strip() : y.strip() for a in applicable_lines for x, y in a.split(':')})

    filter_set = {x for x, y in master_dict.items() if y == "__filter__"}
    sub_set = {x for x, y in master_dict.items() if y not in ("__filter__", "__leave__")}

# Perform the filtering and substituting
logging.info("Performing filter and sub")
for ent in db.entries:
    ent['tags'].difference_update(filter_set)
    inter = ent['tags'].intersection(sub_set)
    ent['tags'].difference_update(inter)
    ent['tags'].update([master_dict[x] for x in inter])
    #transform back to string type:
    ent['tags'] = ", ".join(ent['tags'])


logging.info("Writing")
writer = BibTexWriter()
with open("{}.bib".format(args.output), 'w') as f:
    f.write(writer.write(db))
