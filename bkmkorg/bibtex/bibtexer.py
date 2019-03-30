"""
Script to process bibtex file
Giving stats, non-tagged entries,
year distributions
firstnames, surnames.
"""
import IPython
import bibtexparser as b
from bibtexparser.bparser import BibTexParser
from bibtexparser import customization as c
from os.path import join, isfile, exists, isdir, splitext, expanduser
from os import listdir
import regex as re
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

args.target = expanduser(args.target)
assert(exists(args.target))

logging.info("Targeting: {}".format(args.target))
logging.info("Output to: {}".format(args.output))

parser = BibTexParser(common_strings=False)
parser.ignore_nonstandard_types = False
parser.homogenise_fields = True

def custom(record):
    record = c.type(record)
    record = c.author(record)
    record = c.editor(record)
    record = c.journal(record)
    record = c.keyword(record)
    record = c.link(record)
    record = c.doi(record)
    if "keywords" in record:
        record["keywords"] = [i.strip() for i in re.split(',|;', record["keywords"].replace('\n', ''))]
    if "mendeley-tags" in record:
        record["mendeley-tags"] = [i.strip() for i in re.split(',|;', record["mendeley-tags"].replace('\n', ''))]

    record['p_authors'] = [c.splitname(x, False) for x in record['author']]
    return record

parser.customization = custom

with open(args.target, 'r') as f:
    logging.info("Loading bibtex")
    db = b.load(f, parser)

logging.info("Bibtex loaded")

all_tags = {}
all_years = {}
non_tagged = []
author_counts = {}

logging.info("Processing Entries: {}".format(len(db.entries)))
proportion = int(len(db.entries) / 10)
count = 0
for i, entry in enumerate(db.entries):
    if i % proportion == 0:
        logging.info("{}/10 Complete".format(count))

    #get tags
    if "keywords" in entry:
        tags = set(entry['keywords'])
    else:
        tags = set()
    if "mendeley-tags" in entry:
        tags.update(entry['mendeley-tags'])

    for x in tags:
        if x not in all_tags:
            all_tags[x] = 0
        all_tags[x] += 1

    #get untagged
    if not bool(tags):
        non_tagged.append(entry)

    #count entries per year
    if 'year' in entry:
        if entry['year'] not in all_years:
            all_years[entry['year']] = 0
        all_years[entry['year']] += 1

    #get names
    for x in entry['p_authors']:
        lastname = x['last'][0].lower()
        initial = ""
        if bool(x['first']):
            initial = x['first'][0][0].lower()

        if lastname not in author_counts:
            author_counts[lastname] = {}

        if initial not in author_counts[lastname]:
            author_counts[lastname][initial] = 0

        author_counts[lastname][initial] += 1

logging.info("Processing complete")

tag_str = ["{} : {}".format(k,v) for k,v in all_tags.items()]
with open("{}_tags".format(args.output), 'w') as f:
    logging.info("Writing Tags")
    f.write("\n".join(tag_str))

year_str = ["{} : {}".format(k,v) for k,v in all_years.items()]
with open("{}_years".format(args.output), 'w') as f:
    logging.info("Writing Years")
    f.write("\n".join(year_str))

with open("{}_non_tagged".format(args.output), 'w') as f:
    logging.info("Writing non_tagged")
    f.write("\n".join(non_tagged))

with open("{}_authors".format(args.output), 'w') as f:
    logging.info("Writing authors")
    for lastname, initials_dict in author_counts.items():
        for initial, count in initials_dict.items():
            f.write("{}, {} : {}\n".format(lastname, initial, count))

logging.info("Complete")
IPython.embed(simple_prompt=True)
