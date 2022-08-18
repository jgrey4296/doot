#!/usr/bin/env python

import argparse
import json
import logging as root_logger
from collections import defaultdict
from os import listdir, mkdir
from os.path import (abspath, exists, expanduser, getsize, isdir, isfile, join,
                     split, splitext)
from subprocess import call

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join([""]))
parser.add_argument('--library', action="append", help="where to look for files")
parser.add_argument('--target',  help="json file of variants")
parser.add_argument('--trash',   help="move no longer needed files here")
parser.add_argument('--real',    action='store_true')


##############################

def move_file(file_path, target, is_real):
    assert(isdir(target))
    assert(isfile(file_path))
    logging.info("Moving to %s from %s", target, file_path)
    if is_real:
        call(["mv", file_path, target])


if __name__ == '__main__':
    args    = parser.parse_args()
    library = [abspath(expanduser(x)) for x in args.library]
    target  = abspath(expanduser(args.target))
    trash   = abspath(expanduser(args.trash))

    logging.info("IS REAL: %s", args.real))

    if not exists(trash):
        logging.info("Making Trash Directory: %s", trash))
        mkdir(trash)

    # Collect the media files
    logging.info("Collecting media from: %s", ",".join(library))
    queue = library[:]
    media = defaultdict(lambda: [])
    while bool(queue):
        current = queue.pop(0)
        if isfile(current) and splitext(current)[1] == ".mp4":
            media[split(current)[1]].append(current)
        elif isdir(current):
            queue += [join(current, x) for x in listdir(current) if x != ".git"]

    logging.info("Found %s  media", len(media))

    # Get variants:
    logging.info("Reading variant lists from: %s ", target)
    with open(target, 'r') as f:
        var_text = f.read()
    variants_list = json.loads(var_text)


    logging.info("Building Equivalency lists")
    equivalent_files = []
    for var_url_list in variants_list:
        filenames = [split(x)[1] for x in var_url_list]
        existing = [x for x in filenames if x in media]
        if bool(existing):
            equivalent_files.append(existing)

    logging.info("Found %s equivalents", len(equivalent_files))

    logging.info("Keeping Not-smallest files")
    for equiv_list in equivalent_files:
        paths = [media[x] for x in equiv_list]
        if len(paths) == 1:
            continue

        grouped_by_prefix = defaultdict(lambda: [])

        for group in paths:
            for a_path in group:
                prefix = split(a_path)[0]
                grouped_by_prefix[prefix].append(a_path)

        logging.info("Working with %s prefix groups", len(grouped_by_prefix))
        for prefix_group in grouped_by_prefix.values():
            logging.info("--------------------")
            sized = sorted([(getsize(x), x) for x in prefix_group if exists(x)])
            # keep the largest, to downsize later
            largest = sized.pop()
            logging.info("Keeping: %s", str(largest))
            # Move the rest
            for s, x in sized:
                logging.info("Trashing: %s", s)
                move_file(x, trash, args.real)
