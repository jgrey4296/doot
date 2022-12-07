#!/usr/bin/env python
##-- imports
from __future__ import annotations

import argparse
import json
import logging as root_logger
import pathlib as pl
import re

from bkmkorg.bibtex import parsing as BU
from bkmkorg.files import collect
##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##-- end logging

##-- consts
DEFAULT_PATTERN = re.compile(r"(.*?\[+)/Users/johngrey/Desktop/twitter/orgs/(.+?)(\]\[.+)$")
PERMALINK       = re.compile(r".*?:PERMALINK: *\[\[(.+?)\]\[")
LINK            = re.compile(r".*\[\[(.+?)\]\[")
##-- end consts

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join([""]))
parser.add_argument('--target', action="append", required=True)
parser.add_argument('--media', required=True)
parser.add_argument('--pattern', default=DEFAULT_PATTERN)
##-- end argparse

def retarget_org_file_links(org_file, pattern):
    # read file
    logging.debug("Org file: %s \n %s", org_file, org_file + "_backup")
    with open(org_file, 'r') as f:
        lines = f.readlines()
    # duplicate file
    with open(org_file.with_suffix(".org.backup"), 'w') as f:
        f.write("\n".join(lines))

    # transform file
    new_target = org_file.parent
    retargeted = []
    for line in lines:
        maybe_match = pattern.match(line)
        if not maybe_match:
            retargeted.append(line)
        else:
            # transform line
            new_target_t = new_target /  maybe_match[2]
            newline = pattern.sub(r"\1{}\3".format(new_target_t), line)
            retargeted.append(newline)

    # write file
    with open(org_file, 'w') as f:
        f.write("\n".join([x for x in retargeted]))

def find_media(org_file):
    with open(org_file, 'r') as f:
        lines = f.readlines()

    media = {}
    current_tweet = None
    for line in lines:
        the_match = PERMALINK.match(line)
        if the_match:
            current_tweet = the_match[1]
            continue
        the_match = LINK.match(line)
        if the_match:
            if current_tweet not in media:
                media[current_tweet] = []
            media[current_tweet].append(the_match[1])

    return media


def dfs_for_files(target, ext):
    assert(isinstance(target, list))
    assert(isinstance(ext, list))
    queue = target[:]
    found = []
    while bool(queue):
        current = queue.pop()
        if current.is_dir():
            queue += [x for x in current.iterdir()]
        elif current.is_file() and current.suffix in ext:
            found.append(current)

    return found

##-- ifmain
if __name__ == "__main__":
    my_args = parser.parse_args()
    my_args.media = pl.Path(my_args.media).expanduser().resolve()
    my_args.pattern = re.compile(my_args.pattern)
 
    # find all orgs
    orgs = collect.get_data_files(my_args.target, ".org")
    found_media = {}
    logging.info("Found: %s orgs", len(orgs))
    for org in orgs:
        retarget_org_file_links(org, my_args.pattern)
        found_media.update(find_media(org))

    with open(my_args.media, 'w') as f:
        json.dump(found_media, f)

    # Media:
    # Get exiftool data,
    # Compare distance of creation time, X Y Ratio, duration
    # move similars into separate folder, note its source and similarities

##-- end ifmain
