"""
Split the bookmark library by top level domain
"""

import argparse
import logging as root_logger
from os import mkdir
from os.path import abspath, exists, expanduser, isdir, join, split, splitext
from urllib.parse import urlparse

from bkmkorg.io.writer.org import exportBookmarks as org_export
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
                                    epilog = "\n".join(["Load a bookmark file, split into url netlocs"]))
parser.add_argument('-l', '--library')
parser.add_argument('-o', '--output')
parser.add_argument('-c', '--count', default=200)


if __name__ == "__main__":
    args = parser.parse_args()
    args.library = abspath(expanduser(args.library))
    args.output = abspath(expanduser(args.output))

    if not isdir(args.output):
        mkdir(args.output)

    # load library
    library = open_and_extract_bookmarks(args.library)

    domains = {}

    # Group urls into domains
    for bkmk in library:
        parsed = urlparse(bkmk.url)
        if parsed.netloc not in domains:
            domains[parsed.netloc] = []
        domains[parsed.netloc].append(bkmk)

    misc_count = 0
    write_groups = {}

    # split and group
    for domain, sites in domains.items():
        misc = "misc_{}".format(misc_count)
        if len(sites) > args.count:
            write_groups[domain] = sites
        elif len(write_groups[misc]) + len(sites) < args.count:
            write_groups[misc] += sites
        else:
            misc_count += 1
            misc = "misc_{}".format(misc_count)
            write_groups[misc] = sites

    #save
    for group, sites in write_groups.items():
        org_export(sites, join(args.output, "{}.org".format(group)))
