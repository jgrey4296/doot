#!/usr/bin/env python
import re
import json

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
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir

from bkmkorg.utils import retrieval
from bkmkorg.utils import bibtex as BU


DEFAULT_PATTERN = re.compile("(.*?\[+)/Users/johngrey/Desktop/twitter/orgs/(.+?)(\]\[.+)$")
PERMALINK       = re.compile(r".*?:PERMALINK: *\[\[(.+?)\]\[")
LINK            = re.compile(r".*\[\[(.+?)\]\[")


def retarget_org_file_links(org_file, pattern):
    # read file
    logging.debug("Org file: {} \n {}".format(org_file, org_file + "_backup"))
    with open(org_file, 'r') as f:
        lines = f.readlines()
    # duplicate file
    with open(org_file + "_backup", 'w') as f:
        [f.write(x) for x in lines]

    # transform file
    new_target = split(org_file)[0]
    retargeted = []
    for line in lines:
        maybe_match = pattern.match(line)
        if not maybe_match:
            retargeted.append(line)
        else:
            # transform line
            new_target_t = join(new_target, maybe_match[2])
            newline = pattern.sub(r"\1{}\3".format(new_target_t), line)
            retargeted.append(newline)

    # write file
    with open(org_file, 'w') as f:
        [f.write(x) for x in retargeted]

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
        if isdir(current):
            queue += [join(current, x) for x in listdir(current)]
        elif isfile(current) and splitext(current)[1] in ext:
            found.append(current)

    return found

if __name__ == "__main__":
    import argparse

    #see https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join([""]))
    parser.add_argument('--target', action="append")
    parser.add_argument('--media')
    parser.add_argument('--pattern', default=DEFAULT_PATTERN)

    my_args = parser.parse_args()
    my_args.media = abspath(expanduser(my_args.media))
    my_args.pattern = re.compile(my_args.pattern)
 
    # find all orgs
    orgs = retrieval.get_data_files(my_args.target, ".org")
    found_media = {}
    logging.info("Found: {} orgs".format(len(orgs)))
    for org in orgs:
        retarget_org_file_links(org, my_args.pattern)
        found_media.update(find_media(org))

    with open(my_args.media, 'w') as f:
        json.dump(found_media, f)

    # Media:
    # Get exiftool data,
    # Compare distance of creation time, X Y Ratio, duration
    # move similars into separate folder, note its source and similarities
