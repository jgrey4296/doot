"""
Script to combine multiple bibtex files into one
"""
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from math import ceil
from os import listdir, mkdir
from os.path import join, isfile, exists, isdir, splitext, expanduser, abspath
import IPython
import argparse
import bibtexparser as b
import regex as re
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
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="""Integrates a collection of bibtex files into a single file. Targets can be flat directories""")
parser.add_argument('-t', '--target', action="append")
parser.add_argument('-o', '--output', default="./output/integrated.bib")
args = parser.parse_args()

args.target = [abspath(expanduser(x)) for x in args.target]
args.output = abspath(expanduser(args.output))
assert(all([exists(x) for x in args.target]))


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
    if isdir(x):
        bibtex_files = [y for y in listdir(x) if splitext(y)[1] == ".bib"]
    else:
        bibtex_files = [x]

    for y in bibtex_files:
        with open(join(x,y), 'r') as f:
            logging.info("Loading bibtex: {}".format(y))
            db = b.load(f, parser)
            dbs.append(db)

main_db = None
if exists(args.output):
    parser = BibTexParser(common_strings=False)
    parser.ignore_nonstandard_types = False
    parser.homogenise_fields = True
    parser.customization = custom
    with open(args.output, 'r') as f:
        logging.info("Loading output: {}".format(args.output))
        main_db = b.load(f, parser)
else:
    main_db = b.bibdatabase.BibDatabase()

main_set = set(main_db.get_entry_dict().keys())

missing_entries = []
missing_keys_main = set()
for db in dbs:
    db_dict = db.get_entry_dict()
    db_set = set(db_dict.keys())
    missing_keys = db_set.difference(main_set)
    missing_keys_main.update(missing_keys)
    missing_entries += [db_dict[x] for x in missing_keys]

logging.info("{} missing entries".format(len(missing_entries)))
main_db.entries = missing_entries

logging.info("Bibtex loaded")
writer = BibTexWriter()
with open(join(args.output),'a') as f:
        f.write(writer.write(main_db))
