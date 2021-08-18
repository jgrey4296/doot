#!/usr/bin/env python
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir
import argparse
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

#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join([""]))
parser.add_argument('-s', '--source', action="append")
parser.add_argument('-o', '--output')

from bkmkorg.io.reader.plain_bookmarks import load_plain_file

if __name__ == '__main__':
    args = parser.parse_args()
    args.output = abspath(expanduser(args.output))
    args.source = [abspath(expanduser(x)) for x in args.source]

    bookmarks = []
    for path in args.source:
        bookmarks += load_plain_file(path)

    deduplicated = {}
    for bkmk in bookmarks:
        if bkmk.url not in deduplicated:
            deduplicated[bkmk.url] = bkmk
        else:
            deduplicated[bkmk.url].tags.update(bkmk.tags)

    sorted_keys = sorted(deduplicated.keys())
    key_str     = "\n".join([deduplicated[x].to_string() for x in sorted_keys])
    logging.info(f"Writing out: {len(sorted_keys)}")
    with open(args.output,'w') as f:
        f.write(key_str)
