"""
Split the bookmark library by top level domain
"""

import argparse
import logging as root_logger
from os import mkdir
from os.path import abspath, exists, isdir, join, split, splitext
from urllib.parse import urlparse

from bkmkorg.io.writer.org import exportBookmarks as org_export
from bkmkorg.io.reader.netscape import open_and_extract_bookmarks

if __name__ == "__main__":
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
                                     epilog = "\n".join(["Read a bookmark file, split it into separate files by tag"]))
    parser.add_argument('-l', '--library')
    parser.add_argument('-o', '--output')

    args = parser.parse_args()
    args.library = abspath(expanduser(args.library))
    args.output = abspath(expanduser(args.output))

    if not isdir(args.output):
        logging.info("Making output Directory: {}".format(args.output))
        mkdir(args.output)

    # load library
    library = open_and_extract_bookmarks(args.library)

    tags = {}

    # Group Bookmarks by their tags
    logging.info("Grouping by tags")
    for bkmk in library:
        for tag in bkmk.tags:
            if tag not in tags:
                tags[tag] = []
            tags[tag].append(bkmk)

    # save
    for tag, sites in tags.items():
        logging.info("Exporting: {}".format(tag))
        org_export(sites, join(args.output, "{}.org".format(tag)))
