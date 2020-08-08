"""
Script to read org files and check them for erroneous tags
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

ORG_ID_REGEX = regex.compile("^\s+:(PERMALINK|TIME):\s+$")


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

def check_orgs(org_files):
    logging.info("Checking Orgs")
    files = set([])

    for org in org_files:
        #read
        text = []
        with open(org,'r') as f:
            text = f.readlines()

        #line by line
        for line in text:
            match = ORG_ID_REGEX.match(line)
            if not bool(match):
                continue

            files.add(org)
            break

    return files

#--------------------------------------------------


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join(["Report org files with incorrect meta data of tweets"]))
    parser.add_argument('-t', '--target',action="append")
    parser.add_argument('-o', '--output', default="collected")


    logging.info("Org Check start: --------------------")
    args = parser.parse_args()
    args.target = [abspath(expanduser(x)) for x in args.target]
    args.output = abspath(expanduser(args.output))

    logging.info("Targeting: {}".format(args.target))
    logging.info("Output to: {}".format(args.output))

    bibs, htmls, orgs = collect_files(args.target)
    suspect_files = check_orgs(orgs)

    logging.info("Found {} suspect files".format(len(suspect_files)))
    with open(args.output,'w') as f:
        for id_str in suspect_files:
            f.write("{}\n".format(id_str))

    logging.info("Complete --------------------")
