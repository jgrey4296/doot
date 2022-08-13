"""
Simple program to integrate images into a collection
"""
##-- imports
from __future__ import annotations

import argparse
import logging as root_logger
from hashlib import sha256
from shutil import copyfile

import regex as re
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.file.hash_check import file_to_hash
##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.md5PaperChecker"
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)

##-- end logging

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Find images in {source} dir that are not linked in {output}.org, and link them"]))
parser.add_argument('-s', '--source', required=True)
parser.add_argument('-o', '--output', required=True)
##-- end argparse


##############################

##-- consts
text_template = "** [[file://{}][{}]]\n"
path_re       = re.compile(r'^\*\*+\s+(?:TODO|DONE)?\[\[file:([\w/\.~]+)\]')
file_types    = ['.png', '.gif', '.jpg', '.jpeg']
##-- end consts



if __name__ == "__main__":
    args        = parser.parse_args()
    args.source = pl.Path(args.source).expanduser().resolve()
    args.output = pl.Path(args.output).expanduser().resolve()

    assert(args.output.suffix == '.org')

    logging.info("Loading Existing")
    with open(args.output,'r') as f:
        text = f.read().split('\n')

    logging.info("Finding links")
    path_matches   = [path_re.findall(x) for x in text]
    path_merge     = [y for x in path_matches for y in x]
    expanded_files = [pl.Path(x).expanduser().resolve() for x in path_merge]
    logging.info("Found: {}".format(len(expanded_files)))

    logging.info("Hashing")
    current_hashes = { file_to_hash(x) for x in expanded_files }

    logging.info("Scraping Source Directory")
    imgs_in_dir  = [x for x in args.source.iterdir() if x.suffix.lower() in file_types
                    and x.name[0] != '.']
    logging.info("Scraped: {}".format(len(imgs_in_dir)))

    logging.info("Hashing")
    total_hashes = { file_to_hash(x) : x for x in imgs_in_dir }

    #get the difference
    logging.info("Getting difference of hashes")
    to_add = set(total_hashes.keys()).difference(current_hashes)

    #append unlinked files
    logging.info("Appending to output: {}".format(len(to_add)))
    with open(args.output, 'a') as f:
        for h in to_add:
            filename = total_hashes[h]
            f.write(text_template.format(filename, split(filename)[1]))
