#!/usr/bin/env python
##-- imports
from __future__ import annotations

import pathlib as pl
import argparse
import logging as root_logger
from bkmkorg.utils.bookmarks.collection import BookmarkCollection
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
                                 epilog = "\n".join(["Merge source .bookmark files",
                                                    "Into the output file"]))
parser.add_argument('-s', '--source', action="append", required=True, help="Expects .bookmarks files")
parser.add_argument('-o', '--output', required=True, help="Expects a .bookmarks file")
##-- end argparse


def main():
    args        = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()
    args.source = [pl.path(x).expanduser().resolve() for x in args.source]

    bookmarks = BookmarkCollection()
    for path in args.source:
        bookmarks.add_file(path)

    bookmarks.merge_duplicates()

    logging.info(f"Writing out: {len(bookmarks)}")
    with open(args.output,'w') as f:
        f.write(str(bookmarks))


if __name__ == '__main__':
    main()
