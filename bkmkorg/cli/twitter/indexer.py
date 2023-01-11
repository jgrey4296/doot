#!/usr/bin/env python
##-- imports
from __future__ import annotations

import argparse
import logging as root_logger
import pathlib as pl
import re
from collections import defaultdict

from bkmkorg.files.collect import get_data_files
from bkmkorg.collections.indexfile import IndexFile

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

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Index all users found in orgs"]))
parser.add_argument('--target', action="append", required=True)
parser.add_argument('--output', required=True)
##-- end argparse

##-- consts
# TODO add @ recognition
PERMALINK = re.compile(r':PERMALINK:\s+\[\[https?://twitter.com/(.+?)/status/[0-9]+\]')
##-- end consts


def main():
    logging.info("---------- STARTING Twitter Indexer")
    args        = parser.parse_args()
    args.target = [pl.Path(x).expanduser().resolve() for x in args.target]
    args.output = pl.Path(args.output).expanduser().resolve()

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

##-- ifmain
if __name__ == '__main__':
    main()

##-- end ifmain
