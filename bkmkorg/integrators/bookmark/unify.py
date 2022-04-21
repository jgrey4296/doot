#!/usr/bin/env python
import argparse
import logging as root_logger
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################

#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Merge source .bookmark files",
                                                    "Into the output file"]))
    parser.add_argument('-s', '--source', action="append", required=True, help="Expects .bookmarks files")
parser.add_argument('-o', '--output', required=True, help="Expects a .bookmarks file")

from bkmkorg.utils.bookmarks.collection import BookmarkCollection


def main():
    args        = parser.parse_args()
    args.output = abspath(expanduser(args.output))
    args.source = [abspath(expanduser(x)) for x in args.source]

    bookmarks = BookmarkCollection()
    for path in args.source:
        with open(path, 'r') as f:
            bookmarks.add_file(f)

    bookmarks.merge_duplicates()

    logging.info(f"Writing out: {len(bookmarks)}")
    with open(args.output,'w') as f:
        f.write(str(bookmarks))


if __name__ == '__main__':
    main()
