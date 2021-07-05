"""
Split the bookmark library into Two Files:
All bookmarks where the top level domain occurs more than once
All bookmarks where the top level domain occurs only once
"""

import argparse
import logging as root_logger
from os import mkdir
from os.path import abspath, exists, expanduser, isdir, join, split, splitext
from urllib.parse import urlparse

from bkmkorg.io.writer.netscape import exportBookmarks
from bkmkorg.io.reader.netscape import open_and_extract_bookmarks

# Setup
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Load a bookmark file, split into url netlocs [many/one]"]))
parser.add_argument('-l', '--library')
parser.add_argument('-o', '--output')


if __name__ == "__main__":
    args = parser.parse_args()
    args.library = abspath(expanduser(args.library))
    args.output = abspath(expanduser(args.output))

    if not isdir(args.output):
        mkdir(args.output)

    # load library
    library = open_and_extract_bookmarks(args.library)

    domains = {}

    # group into domains
    for bkmk in library:
        parsed = urlparse(bkmk.url)
        if parsed.netloc not in domains:
            domains[parsed.netloc] = []
        domains[parsed.netloc].append(bkmk)

    many = []
    ones = []

    # split and write into groups
    for domain, sites in domains.items():
        if len(sites) > 1:
            many += sites
        else:
            ones += sites

    #save
    exportBookmarks(many, join(args.output, "multiple_instances.html"))
    exportBookmarks(ones, join(args.output, "single_instances.html"))
