#!/usr/bin/env python
"""
Script to process bibtex file
Giving stats, non-tagged entries,
year distributions
firstnames, surnames.
"""
import argparse
import logging as root_logger
from math import ceil
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from collections import defaultdict

import bibtexparser as b
import regex as re
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser

from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.file import retrieval

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

# Setup
console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog="\n".join(["Describe a bibtex file's:",
                                                    "Tags, year counts, authors,",
                                                    "And entries lacking files or with multiple files"]))
parser.add_argument('-t', '--target', default="~/github/writing/resources", help="Input target")
parser.add_argument('-o', '--output', default="bibtex",                     help="Output Target")
parser.add_argument('-f', '--files', action="store_true",                   help="Write to files")
parser.add_argument('-a', '--authors', action="store_true",                 help="Describe authors")
parser.add_argument('-y', '--years', action="store_true",                   help="Describe Years")


def make_bar(k, v, left_pad_v, right_scale_v):
    pad = ((10 + left_pad_v) - len(k))
    bar_graph = ceil(((100 - pad) / right_scale_v) * v)
    full_str = "{}{}({}) : {}>\n".format(k, " " * pad, v, "=" *  bar_graph)
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
        record['p_authors'] = [x.split(' and ') for x in record['author']]
    return record




def process_db(db):

    proportion = int(len(db.entries) / 10)
    count = 0

    # Extracted data
    all_keys               = []
    all_tags               = defaultdict(lambda: 0)
    all_years              = defaultdict(lambda: 0)
    author_counts          = defaultdict(lambda: 0)
    non_tagged             = []
    no_file                = []
    missing_files          = []

    # Enumerate over all entries, updated data
    for i, entry in enumerate(db.entries):
        # Log progress
        if i % proportion == 0:
            logging.info(f"{count}/10 Complete")
            count += 1

        if entry['ID'] in all_keys:
            logging.warning("Duplicate Key: {}".format(entry['ID']))

        all_keys.append(entry['ID'])
        # get tags
        e_tags = entry['tags']

        for x in e_tags:
            all_tags[x] += 1

        # get untagged
        if not bool(e_tags):
            non_tagged.append(entry)

        # count entries per year
        if 'year' in entry:
            all_years[entry['year']] += 1

        # count names
        for x in entry['p_authors']:
            for name in x:
                author_counts[name] += 1

        # Retrieve file information
        if not any(['file' in x for x in entry.keys()]):
            no_file.append(entry['ID'])

        else:
            filenames = [y for x,y in entry.items() if 'file' in x]
            missing_files += [y for y in filenames if not exists(y)]

    return (all_keys,
            all_tags,
            all_years,
            author_counts,
            non_tagged,
            no_file,
            missing_files)

def build_tag_files(all_tags, target):
    # Build Tag count file
    tag_str = ["{} : {}".format(k, v) for k, v in all_tags.items()]
    with open("{}.tag_counts".format(target), 'w') as f:
        logging.info("Writing Tag Counts")
        f.write("\n".join(tag_str))

    # Build All Tags set File
    with open("{}.all_tags".format(target), 'w') as f:
        logging.info("Writing all Tags")
        f.write("\n".join([x for x in all_tags.keys()]))



def build_year_counts(all_years, target):
    # Build Year counts file
    logging.info("Writing Year Descriptions")
    year_str = ["{} : {}".format(k,v) for k,v in all_years.items()]
    with open("{}.years".format(target), 'w') as f:
        f.write("\n".join(year_str))
        longest_year = 10 + max([len(x) for x in all_years.keys()])
        most_year = max([x for x in all_years.values()])

def build_author_counts(author_counts, target):
    logging.info("Writing Author Descriptions")
    longest_author = 10 + max([len(x) for x in author_counts.keys()])
    most_author = max([x for x in author_counts.values()])
    with open("{}.authors".format(target), 'w') as f:
        with open("{}.authors_bar".format(target), 'w') as g:
            logging.info("Writing authors")
            for name, count in author_counts.items():
                f.write("{} : {}\n".format(name, count))
                g.write(make_bar(name, count, longest_author, most_author))


def main():
    args = parser.parse_args()

    args.output = abspath(expanduser(args.output))
    assert(exists(args.target))

    logging.info("Targeting: {}".format(args.target))
    logging.info("Output to: {}".format(args.output))

    # Load targets
    bib_files = retrieval.get_data_files(args.target, ".bib")
    db = BU.parse_bib_files(bib_files, func=custom)
    logging.info("Bibtex loaded")

    logging.info(f"Processing Entries: {len(db.entries)}")
    result = process_db(db)
    logging.info("Processing complete")
    build_tag_files(result[1], args.output)

    if args.years:
        build_year_counts(result[2], args.output)

    # Build Author counts files
    if args.authors:
        build_author_counts(result[3], args.output)

    # Build Default Files
    if args.files:
        logging.info("Writing Descriptions of Files")
        with open(f"{args.output}.no_file", 'w') as f:
            f.write("\n".join(result[5]))

        with open(f"{args.output}.missing_file", 'w') as f:
            f.write("\n".join(result[6]))

    logging.info("Complete")


if __name__ == "__main__":
    main()
