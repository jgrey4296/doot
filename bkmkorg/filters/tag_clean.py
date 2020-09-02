"""
Script to Process Bibtex, bookmark, and org files for tags
and to clean them
"""
from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bkmkorg.bookmark_data import bookmarkTuple
from bkmkorg.io.export_netscape import exportBookmarks
from bkmkorg.io.import_netscape import open_and_extract_bookmarks
from math import ceil
from os import listdir
from os.path import join, isfile, exists, isdir, splitext, expanduser, abspath, split
import argparse
import bibtexparser as b
import logging as root_logger
import regex
import regex as re

logging = root_logger.getLogger(__name__)

ORG_TAG_REGEX = regex.compile("^\*\*\s+(.+?)(\s+):(\S+):$")
BIB_TAG_REGEX = regex.compile("^(\s*tags\s*=\s*{)(.+?)(\s*},?)$")
##############################
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join(["Extracts all tags in all bibtex, bookmark and org files in specified dirs"]))
parser.add_argument('-t', '--target',action="append")
parser.add_argument('-c', '--cleaned', action="append")

bparser = BibTexParser(common_strings=False)
bparser.ignore_nonstandard_types = False
bparser.homogenise_fields = True

def custom(record):
    # record = c.type(record)
    # record = c.author(record)
    # record = c.editor(record)
    # record = c.journal(record)
    # record = c.keyword(record)
    # record = c.link(record)
    # record = c.doi(record)
    tags = set()

    if 'tags' in record:
        tags.update([i.strip() for i in re.split(',|;', record["tags"].replace('\n', ''))])
    if "keywords" in record:
        tags.update([i.strip() for i in re.split(',|;', record["keywords"].replace('\n', ''))])
    if "mendeley-tags" in record:
        tags.update([i.strip() for i in re.split(',|;', record["mendeley-tags"].replace('\n', ''))])

    record['tags'] = tags
    # record['p_authors'] = []
    # if 'author' in record:
    #     record['p_authors'] = [c.splitname(x, False) for x in record['author']]
    return record


bparser.customization = custom

def collect_tags(targets):
    """ DFS targets, get tags, """
    logging.info("Collecting Tags")
    tag_substitutor = {}
    remaining = targets[:]
    processed = set([])
    while bool(remaining):
        current = remaining.pop(0)
        if current in processed:
            continue
        if isfile(current):
            ext = splitext(current)[1]
            if ext == ".tags":
                #read raw tags
                tag_substitutor.update(read_raw_tags(current))
            elif ext == ".org":
                #read_org file
                tag_substitutor.update(read_org_tags(current))

            processed.add(current)
        else:
            assert(isdir(current))
            subdirs = [join(current, x) for x in listdir(current)]
            remaining += subdirs


    return tag_substitutor

def read_raw_tags(target):
    """ Read a text file of the form:
    tag : num : sub : sub : sub....
    returning a dict of {tag : [sub]}
    """
    lines = []
    sub = {}
    with open(target,'r') as f:
        lines = f.readlines()

    #split and process
    for line in lines:
        components = line.split(":")
        assert(components[0].strip() not in sub)
        sub[components[0].strip()] = []
        if len(components) > 2:
            sub[components[0].strip()] += [x.strip() for x in components[2:]]

    return sub

def read_org_tags(target):
    """ Read an org file headings and lines of form:
    tag : num : sub : sub : sub : sub...
    returning a dict of {tag: [sub]}
    """
    lines = []
    sub = {}
    with open(target,'r') as f:
        lines = f.readlines()

    #split and process
    for line in lines:
        if line[0] == "*":
            continue
        components = line.split(":")
        assert(components[0].strip() not in sub)
        sub[components[0].strip()] = []
        if len(components) > 2:
            sub[components[0].strip()] += [x.strip() for x in components[2:]]

    return sub


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

def clean_bib_files(bib_files, sub):
    """ Parse all the bibtext files """
    for bib in bib_files:
        lines = []
        out_lines = []
        with open(bib, 'r') as f:
            lines = f.readlines()
        logging.info("Bibtex loaded")

        for line in lines:
            match = BIB_TAG_REGEX.match(line)
            if match is None:
                out_lines.append(line)
                continue

            tags = [x.strip() for x in match[2].split(",")]
            replacement_tags = set([])
            for tag in tags:
                if tag in sub and bool(sub[tag]):
                    [replacement_tags.add(new_tag) for new_tag in sub[tag]]
                else:
                    replacement_tags.add(tag)
            out_lines.append("{}{}{}\n".format(match[1],
                                             ",".join(replacement_tags),
                                             match[3]))

        outstring = "".join(out_lines)
        with open(bib, 'w') as f:
            f.write(outstring)

def clean_org_files(org_files, sub):
    logging.info("Cleaning orgs")
    org_tags = {}

    for org in org_files:
        #read
        text = []
        with open(org,'r') as f:
            text = f.readlines()

        out_text = ""
        #line by line
        for line in text:
            matches = ORG_TAG_REGEX.match(line)

            if not bool(matches):
                out_text += line
                continue

            title = matches[1]
            spaces = matches[2]
            tags = matches[3]

            individual_tags = [x for x in tags.split(':') if x != '']
            replacement_tags = set([])
            #swap to dict:
            for tag in individual_tags:
                if tag in sub and bool(sub[tag]):
                    [replacement_tags.add(new_tag) for new_tag in sub[tag]]
                else:
                    replacement_tags.add(tag)

            out_line = "** {}{}:{}:\n".format(title,
                                              spaces,
                                              ":".join(replacement_tags))
            out_text += out_line
        # write out
        with open(org, 'w') as f:
            f.write(out_text)

def clean_html_files(html_files, sub):
    logging.info("Cleaning htmls")
    html_tags = {}

    for html in html_files:
        bkmks = open_and_extract_bookmarks(html)
        cleaned_bkmks = []
        for bkmk in bkmks:
            replacement_tags = set([])
            for tag in bkmk.tags:
                # clean
                if tag in sub and bool(sub[tag]):
                    [replacement_tags.add(new_tag) for new_tag in sub[tag]]
                else:
                    replacement_tags.add(tag)
            new_bkmk = bookmarkTuple(bkmk.name, bkmk.url, replacement_tags)
            cleaned_bkmks.append(new_bkmk)
        # write out
        exportBookmarks(cleaned_bkmks, html)


#--------------------------------------------------
if __name__ == "__main__":
    logging.info("Tag Cleaning start: --------------------")
    LOGLEVEL = root_logger.DEBUG
    LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
    root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

    console = root_logger.StreamHandler()
    console.setLevel(root_logger.INFO)
    root_logger.getLogger('').addHandler(console)
    logging = root_logger.getLogger(__name__)

    args = parser.parse_args()
    args.target = [abspath(expanduser(x)) for x in args.target]
    args.cleaned = [abspath(expanduser(x)) for x in args.cleaned]

    logging.info("Targeting: {}".format(args.target))
    logging.info("Cleaning based on: {}".format(args.cleaned))

    #Load Cleaned Tags
    cleaned_tags = collect_tags(args.cleaned)
    logging.info("Loaded {} tag substitutions".format(len(cleaned_tags)))

    #Load Bibtexs, html, orgs and clean each
    bibs, htmls, orgs = collect_files(args.target)
    clean_bib_files(bibs, cleaned_tags)
    clean_org_files(orgs, cleaned_tags)
    clean_html_files(htmls, cleaned_tags)
    logging.info("Complete --------------------")
