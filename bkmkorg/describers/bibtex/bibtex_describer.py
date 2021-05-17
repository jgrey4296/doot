"""
Script to process bibtex file
Giving stats, non-tagged entries,
year distributions
firstnames, surnames.
"""
import logging as root_logger
import argparse
from math import ceil
from os import listdir
from os.path import join, isfile, exists, isdir, splitext, expanduser, abspath, split
import regex as re
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
import bibtexparser as b
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

from bkmkorg.utils import retrieval
from bkmkorg.utils import bibtex as BU

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



if __name__ == "__main__":
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

    args = parser.parse_args()

    args.output = abspath(expanduser(args.output))
    assert(exists(args.target))

    logging.info("Targeting: {}".format(args.target))
    logging.info("Output to: {}".format(args.output))

    # Load targets
    bib_files = retrieval.get_data_files(args.target, ".bib")
    db = BU.parse_bib_files(bib_files, func=custom)
    logging.info("Bibtex loaded")

    # Extracted data
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

    # Enumerate over all entries, updated data
    for i, entry in enumerate(db.entries):
        # Log progress
        if i % proportion == 0:
            logging.info("{}/10 Complete".format(count))
            count += 1

        # get tags
        e_tags = entry['tags']

        for x in e_tags:
            if x not in all_tags:
                all_tags[x] = 0
            all_tags[x] += 1

        # get untagged
        if not bool(e_tags):
            non_tagged.append(entry)

        # count entries per year
        if 'year' in entry:
            if entry['year'] not in all_years:
                all_years[entry['year']] = 0
            all_years[entry['year']] += 1

        # count names
        for x in entry['p_authors']:
            for name in x:
                if name not in author_counts:
                    author_counts[name] = 0

                author_counts[name] += 1

        # Retrieve file information
        if not 'file' in entry:
            no_file.append(entry['ID'])
        else:
            # TODO: handle multiple file fields
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

    # Build Tag count file
    tag_str = ["{} : {}".format(k, v) for k, v in all_tags.items()]
    with open("{}.tag_counts".format(args.output), 'w') as f:
        logging.info("Writing Tag Counts")
        f.write("\n".join(tag_str))

    # Build All Tags set File
    with open("{}.all_tags".format(args.output), 'w') as f:
        logging.info("Writing all Tags")
        f.write("\n".join([x for x in all_tags.keys()]))

    # longest_tag = 10 + max([len(x) for x in all_tags.keys()])
    # most_tags = max([x for x in all_tags.values()])
    # tag_bar = []

    # Build Year counts file
    if args.years:
        logging.info("Writing Year Descriptions")
        year_str = ["{} : {}".format(k,v) for k,v in all_years.items()]
        with open("{}.years".format(args.output), 'w') as f:
            f.write("\n".join(year_str))
        longest_year = 10 + max([len(x) for x in all_years.keys()])
        most_year = max([x for x in all_years.values()])


    # Build Author counts files
    if args.authors:
        logging.info("Writing Author Descriptions")
        longest_author = 10 + max([len(x) for x in author_counts.keys()])
        most_author = max([x for x in author_counts.values()])
        with open("{}.authors".format(args.output), 'w') as f:
            with open("{}.authors_bar".format(args.output), 'w') as g:
                logging.info("Writing authors")
                for name, count in author_counts.items():
                    f.write("{} : {}\n".format(name, count))
                    g.write(make_bar(name, count, longest_author, most_author))

    # Build Default Files
    if args.files:
        logging.info("Writing Descriptions of Files")
        with open("{}.no_file".format(args.output), 'w') as f:
            f.write("\n".join(no_file))

        with open("{}.multi_files".format(args.output), 'w') as f:
            f.write("\n".join(multi_files))

        with open("{}.multi_files_duplicates".format(args.output), 'w') as f:
            f.write("\n".join(multi_files_duplicates))

        with open("{}.missing_file".format(args.output), 'w') as f:
            f.write("\n".join(missing_file))

    logging.info("Complete")
