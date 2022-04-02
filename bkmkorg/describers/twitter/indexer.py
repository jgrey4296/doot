#!/usr/bin/env python
import argparse
import logging as root_logger
import re
from collections import defaultdict
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

from bkmkorg.utils.dfs.files import get_data_files
from bkmkorg.utils.indices.collection import IndexFile

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Index all users found in orgs"]))
parser.add_argument('--target', action="append", required=True)
parser.add_argument('--output', required=True)


PERMALINK = re.compile(r':PERMALINK:\s+\[\[https?://twitter.com/(.+?)/status/[0-9]+\]')
# TODO add @ recognition

def main():
    logging.info("---------- STARTING Twitter Indexer")
    args = parser.parse_args()
    args.target = [abspath(expanduser(x)) for x in args.target]
    args.output = abspath(expanduser(args.output))

    targets = get_data_files(args.target, ext=".org")

    index = IndexFile()

    for filename in targets:
        # read in
        lines = []
        with open(filename, 'r') as f:
            lines = f.readlines()

        # PERMALINK
        matched = [PERMALINK.match(x) for x in lines]
        users   = ["@"+x[1] for x in matched if bool(x)]
        # add to index
        for user in users:
            index.add_files(user, [filename])

    # Write out index
    out_string = str(index)
    with open(args.output, 'w') as f:
        f.write(out_string)

    logging.info("Twitter Indexing Finished")

if __name__ == '__main__':
    main()
