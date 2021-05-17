"""
Simple program to integrate images into a collection
"""
from hashlib import sha256
from os import listdir, mkdir
from os.path import join, isfile, exists, isdir, splitext, expanduser, split, abspath
from shutil import copyfile
import argparse
import logging as root_logger
import regex as re

from bkmkorg.utils import retrieval
from bkmkorg.utils import bibtex as BU

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.md5PaperChecker"
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################

text_template = "** [[file://{}][{}]]\n"
path_re = re.compile(r'^\*\*+\s+(?:TODO|DONE)?\[\[file:([\w/\.~]+)\]')
file_types = ['.png', '.gif', '.jpg', '.jpeg']



if __name__ == "__main__":
    # Setup
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join(["Find images in {source} dir that are not linked in {output}.org, and link them"]))
    parser.add_argument('-s', '--source')
    parser.add_argument('-o', '--output')

    args = parser.parse_args()
    args.source = abspath(expanduser(args.source))
    args.output = abspath(expanduser(args.output))

    assert(splitext(args.output)[1] == '.org')

    logging.info("Loading Existing")
    with open(args.output,'r') as f:
        text = f.read().split('\n')

    logging.info("Finding links")
    path_matches = [path_re.findall(x) for x in text]
    path_merge = [y for x in path_matches for y in x]
    expanded_files = [abspath(expanduser(x)) for x in path_merge]
    logging.info("Found: {}".format(len(expanded_files)))

    logging.info("Hashing")
    current_hashes = { fileToHash(x) for x in expanded_files }

    logging.info("Scraping Source Directory")
    files_in_dir = listdir(args.source)
    imgs_in_dir = [x for x in files_in_dir if splitext(x)[1].lower() in file_types
                   and x[0] != '.']
    full_paths = [abspath(expanduser(join(args.source, x))) for x in imgs_in_dir]
    logging.info("Scraped: {}".format(len(full_paths)))

    logging.info("Hashing")
    total_hashes = { fileToHash(x) : x for x in full_paths }

    #get the difference
    logging.info("Getting difference of hashes")
    to_add = set(total_hashes.keys()).difference(current_hashes)

    #append unlinked files
    logging.info("Appending to output: {}".format(len(to_add)))
    with open(args.output, 'a') as f:
        for h in to_add:
            filename = total_hashes[h]
            f.write(text_template.format(filename, split(filename)[1]))
