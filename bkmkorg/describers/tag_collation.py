"""
Script to Process Bibtex, bookmark, and org files for tags
and to collect them
"""
import logging as root_logger
import argparse
from math import ceil
from os import listdir
from os.path import join, isfile, exists, isdir, splitext, expanduser, abspath, split
from bkmkorg.io.import_netscape import open_and_extract_bookmarks
import regex as re
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
import bibtexparser as b
import regex
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)

ORG_TAG_REGEX = regex.compile("^\*\*\s+.+?\s+:(\S+):$")
##############################
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join(["Extracts all tags in all bibtex, bookmark and org files in specified dirs"]))
parser.add_argument('-t', '--target',action="append")
parser.add_argument('-o', '--output', default="collected")

bparser = BibTexParser(common_strings=False)
bparser.ignore_nonstandard_types = False
bparser.homogenise_fields = True

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


bparser.customization = custom

def collect_files(targets):
    """ DFS targets, collecting files into their types """
    logging.info("Processing Files: {}".format(targets))
    bib_files = set()
    html_files = set()
    org_files = set()

    processed = set([])
    remaining_dirs = targets[:]
    while bool(remaining_dirs):
        target = remaining_dirs.pop(0)
        if target in processed:
            continue
        processed.add(target)
        if isfile(target):
            ext = splitext(target)[1]
            if ext == ".bib":
                bib_files.add(target)
            elif ext == ".html":
                html_files.add(target)
            elif ext == ".org":
                org_files.add(target)
        else:
            assert(isdir(target))
            subdirs = [join(target, x) for x in listdir(target)]
            remaining_dirs += subdirs

    logging.info("Split into: {} bibtex files, {} html files and {} org files".format(len(bib_files),
                                                                                      len(html_files),
                                                                                      len(org_files)))
    logging.debug("Bibtex files: {}".format("\n".join(bib_files)))
    logging.debug("Html Files: {}".format("\n".join(html_files)))
    logging.debug("Org Files: {}".format("\n".join(org_files)))

    return (bib_files, html_files, org_files)

def parse_bib_files(bib_files):
    """ Parse all the bibtext files into a shared database """
    db = b.bibdatabase.BibDatabase()
    for x in bib_files:
        with open(x, 'r') as f:
            logging.info("Loading bibtex: {}".format(x))
            db = b.load(f, bparser)
    logging.info("Bibtex loaded")
    return db

def extract_tags_from_bibtex(db):
    logging.info("Processing Bibtex: {}".format(len(db.entries)))
    proportion = int(len(db.entries) / 10)
    count = 0
    bib_tags = {}
    for i, entry in enumerate(db.entries):
        if i % proportion == 0:
            logging.info("{}/10 Complete".format(count))
            count += 1

        #get tags
        e_tags = entry['tags']
        for x in e_tags:
            if x not in bib_tags:
                bib_tags[x] = 0
            bib_tags[x] += 1
    return bib_tags

def extract_tags_from_org_files(org_files):
    logging.info("Extracting data from orgs")
    org_tags = {}

    for org in org_files:
        #read
        text = []
        with open(org,'r') as f:
            text = f.readlines()

        #line by line
        for line in text:
            tags = ORG_TAG_REGEX.findall(line)
            individual_tags = []
            if not bool(tags):
                continue

            individual_tags = [x for x in tags[0].split(':') if x != '']
            #Add to dict:
            for tag in individual_tags:
                if tag not in org_tags:
                    org_tags[tag] = 0
                org_tags[tag] += 1

    return org_tags

def extract_tags_from_html_files(html_files):
    logging.info("Extracting data from htmls")
    html_tags = {}

    for html in html_files:
        bkmks = open_and_extract_bookmarks(html)
        for bkmk in bkmks:
            for tag in bkmk.tags:
                if tag not in html_tags:
                    html_tags[tag] = 0
                html_tags[tag] += 1

    return html_tags

def combine_all_tags(dict_array):
    logging.info("Combining tags")
    all_tags = {}

    for tag_dict in dict_array:
        for tag,count in tag_dict.items():
            if tag not in all_tags:
                all_tags[tag] = 0
            all_tags[tag] += count

    return all_tags

def write_tags(all_tags, output_target):
    tag_str = ["{} : {}".format(k, v) for k, v in all_tags.items()]
    with open("{}.tags".format(output_target), 'w') as f:
        logging.info("Writing Tag Counts")
        f.write("\n".join(tag_str))

#--------------------------------------------------


if __name__ == "__main__":
    logging.info("Tag Collation start: --------------------")
    args = parser.parse_args()
    args.target = [abspath(expanduser(x)) for x in args.target]
    args.output = abspath(expanduser(args.output))

    logging.info("Targeting: {}".format(args.target))
    if isdir(args.output):
        args.output = join(args.output, "tags")
    logging.info("Output to: {}".format(args.output))

    bibs, htmls, orgs = collect_files(args.target)
    bib_db = parse_bib_files(bibs)
    bib_tags = extract_tags_from_bibtex(bib_db)
    org_tags = extract_tags_from_org_files(orgs)
    html_tags = extract_tags_from_html_files(htmls)
    all_tags = combine_all_tags([bib_tags, org_tags, html_tags])
    write_tags(bib_tags, args.output + "_bib")
    write_tags(org_tags, args.output + "_orgs")
    write_tags(html_tags, args.output + "_htmls")
    write_tags(all_tags, args.output)
    logging.info("Complete --------------------")
