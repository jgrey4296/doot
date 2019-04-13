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
##############################

#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser("")
parser.add_argument('-t', '--target', default="~/Mega/library.bib")
parser.add_argument('-o', '--output', default="bibtex")
args = parser.parse_args()

args.target = abspath(expanduser(args.target))
args.output = abspath(expanduser(args.output))
assert(exists(args.target))

logging.info("Targeting: {}".format(args.target))
logging.info("Output to: {}".format(args.output))

parser = BibTexParser(common_strings=False)
parser.ignore_nonstandard_types = False
parser.homogenise_fields = True

def make_bar(k, v, left_pad_v, right_scale_v):
        pad = ((10 + left_pad_v) - len(k))
        bar = ceil(((100 - pad) / right_scale_v) * v)
        full_str = "{}{}({}) : {}>\n".format(k, " " * pad, v, "=" *  bar)
        return full_str

def custom(record):
    record = c.type(record)
    record = c.author(record)
    record = c.editor(record)
    record = c.journal(record)
    record = c.keyword(record)
    record = c.link(record)
    record = c.doi(record)
    tags = set()

    if 'tags' in record:
        tags.update([i.strip() for i in re.split(',|;', record["tags"].replace('\n', ''))])
    if "keywords" in record:
        tags.update([i.strip() for i in re.split(',|;', record["keywords"].replace('\n', ''))])
    if "mendeley-tags" in record:
        tags.update([i.strip() for i in re.split(',|;', record["mendeley-tags"].replace('\n', ''))])

    record['tags'] = tags
    record['p_authors'] = []
    if 'author' in record:
        record['p_authors'] = [c.splitname(x, False) for x in record['author']]
    return record

parser.customization = custom

with open(args.target, 'r') as f:
    logging.info("Loading bibtex")
    db = b.load(f, parser)

logging.info("Bibtex loaded")

all_keys = []
all_tags = {}
all_years = {}
non_tagged = []
author_counts = {}

no_file = []
multi_files = []
multi_files_duplicates = []
missing_file = []

logging.info("Processing Entries: {}".format(len(db.entries)))
proportion = int(len(db.entries) / 10)
count = 0
for i, entry in enumerate(db.entries):
    if i % proportion == 0:
        logging.info("{}/10 Complete".format(count))
        count += 1

    #get tags
    tags = entry['tags']

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

    if not 'file' in entry:
        no_file.append(entry['ID'])
    else:
        if ";" in entry['file']:
            multi_files.append(entry['ID'])
            files = entry['file'].split(';')
            filenames = set([])
            for x in files:
                filenames.add([y for y in x.split(':') if bool(x)][0])
            if len(filenames) > 1:
                multi_files_duplicates.append(entry['file'])
            any_file_exists = any([exists(x) for x in filenames])
            if not any_file_exists:
                missing_file.append(entry['ID'])

        else:
            filename = [x for x in entry['file'].split(':') if bool(x)][0]
            if not exists(filename):
                missing_file.append(entry['ID'])


#--------------------------------------------------
logging.info("Processing complete")

tag_str = ["{} : {}".format(k,v) for k,v in all_tags.items()]
with open("{}_tags".format(args.output), 'w') as f:
    logging.info("Writing Tags")
    f.write("\n".join(tag_str))

with open("{}_all_tags".format(args.output), 'w') as f:
    logging.info("Writing all Tags")
    f.write("\n".join([x for x in all_tags.keys()]))

longest_tag = 10 + max([len(x) for x in all_tags.keys()])
most_tags = max([x for x in all_tags.values()])
tag_bar = []
# with open("{}_tags_bar".format(args.output), 'w') as f:
#     logging.info("Writing Tags Bar")
#     for k,v in all_tags.items():
#         f.write(make_bar(k, v, longest_tag, most_tags))

year_str = ["{} : {}".format(k,v) for k,v in all_years.items()]
with open("{}_years".format(args.output), 'w') as f:
    logging.info("Writing Years")
    f.write("\n".join(year_str))

longest_year = 10 + max([len(x) for x in all_years.keys()])
most_year = max([x for x in all_years.values()])

# with open("{}_years_bar".format(args.output), 'w') as f:
#     logging.info("Writing Years")
#     for k,v in all_years.items():
#         f.write(make_bar(k, v, longest_year, most_year))

# with open("{}_non_tagged".format(args.output), 'w') as f:
#     logging.info("Writing non_tagged")
#     f.write("\n".join(non_tagged))

longest_author = 10 + max([len(x) for x in author_counts.keys()])
most_author = max([y for x in author_counts.values() for y in x.values()])
with open("{}_authors".format(args.output), 'w') as f:
    with open("{}_authors_bar".format(args.output), 'w') as g:
        logging.info("Writing authors")
        for lastname, initials_dict in author_counts.items():
            for initial, count in initials_dict.items():
                f.write("{}, {} : {}\n".format(lastname, initial, count))
                ln_i = "{} {}".format(lastname, initial)
                g.write(make_bar(ln_i, count, longest_author, most_author))


with open("{}_no_file".format(args.output), 'w') as f:
    f.write("\n".join(no_file))

with open("{}_multi_files".format(args.output), 'w') as f:
    f.write("\n".join(multi_files))

with open("{}_multi_files_duplicates".format(args.output), 'w') as f:
    f.write("\n".join(multi_files_duplicates))

with open("{}_missing_file".format(args.output), 'w') as f:
    f.write("\n".join(missing_file))

logging.info("Complete")
IPython.embed(simple_prompt=True)
