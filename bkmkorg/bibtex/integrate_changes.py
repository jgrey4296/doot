"""
Script to combine multiple bibtex files into one
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
parser.add_argument('-t', '--target', action="append")
parser.add_argument('-o', '--output', default="./output/integrated")
args = parser.parse_args()

args.target = [abspath(expanduser(x)) for x in args.target]
args.output = abspath(expanduser(args.output))
assert(all([exists(x) for x in args.target]))

if not isdir(args.output):
    mkdir(args.output)


logging.info("Targeting: {}".format(args.target))
logging.info("Output to: {}".format(args.output))

def custom(record):
    # record = c.type(record)
    # record = c.author(record)
    # record = c.editor(record)
    # record = c.journal(record)
    # record = c.keyword(record)
    # record = c.link(record)
    # record = c.doi(record)
    # if "keywords" in record:
    #     record["keywords"] = [i.strip() for i in re.split(',|;', record["keywords"].replace('\n', ''))]
    # if "mendeley-tags" in record:
    #     record["mendeley-tags"] = [i.strip() for i in re.split(',|;', record["mendeley-tags"].replace('\n', ''))]

    # record['p_authors'] = []
    # if 'author' in record:
    #     record['p_authors'] = [c.splitname(x, False) for x in record['author']]
    return record

#load each of the specified files
dbs = []
for x in args.target:
    parser = BibTexParser(common_strings=False)
    parser.ignore_nonstandard_types = False
    parser.homogenise_fields = True
    parser.customization = custom
    with open(x, 'r') as f:
        logging.info("Loading bibtex: {}".format(x))
        db = b.load(f, parser)
        dbs.append(db)

main = dbs[0]
#Load in all keys and check for conflicts
keys = {}
not_in_main = []
conflicts = {}
on_main = True
for db in dbs:
    for entry in db.entries:
        if entry['ID'] not in keys:
            keys[entry['ID']] = entry
            if not on_main:
                not_in_main.append(entry)
            continue
        elif entry['ID'] not in conflicts:
            conflicts[entry['ID']] = []
        conflicts[entry['ID']].append(entry)

    on_main = False

logging.info("Conflicts: ")
for k,v in conflicts.items():
    orig = keys[k]
    logging.info("Original: {} - {} - {} - {}".format(orig['ID'], orig['author'], orig['year'], orig['title']))
    for c in v:
        logging.info("Conflict: {} - {} - {} - {}".format(c['ID'], c['author'], c['year'], c['title']))
    logging.info("-----")

IPython.embed(simple_prompt=True)

main.entries += not_in_main

logging.info("Bibtex loaded")
writer = BibTexWriter()
with open(join(args.output, "integrated.bib"),'w') as f:
        f.write(writer.write(main))
