"""
Stat generator for bookmarks
Pairs with bkmkorg/filters/bookmark_tag_filter
"""

import argparse
import logging as root_logger
from os.path import abspath, exists, expanduser, split, splitext
from urllib.parse import urlparse

from bkmkorg.io.import.import_netscape import open_and_extract_bookmarks
from bkmkorg.utils import retrieval
from bkmkorg.utils.bibtex import parsing as BU

if __name__ == "__main__":
    # Setup logging
    LOGLEVEL = root_logger.DEBUG
    LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
    root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

    console = root_logger.StreamHandler()
    console.setLevel(root_logger.INFO)
    root_logger.getLogger('').addHandler(console)
    logging = root_logger.getLogger(__name__)

    # Setup
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["For a bookmark file, print out domain counts and tag counts",
                                                     "Pairs with bkmkorg/filters/bookmark_tag_filter"]))
    parser.add_argument('-l', '--library')
    parser.add_argument('-o', '--output')
    parser.add_argument('-t', '--tag', action="store_true")
    parser.add_argument('-d', '--domain', action="store_true")

    args = parser.parse_args()
    args.library = abspath(expanduser(args.library))
    args.output = abspath(expanduser(args.output))

    assert(exists(args.library))

    # Load the library
    logging.info("Loading Library")
    lib_files = retrival.get_data_files(args.library, ".html")
    library = [y for x in lib_files for y in open_and_extract_bookmarks(x)]

    tags = {}
    domains = {}

    # Process library for tags and domains
    logging.info("Processing Library")
    for bkmk in library:
        # Count websites
        parsed = urlparse(bkmk.url)
        if parsed.netloc not in domains:
            domains[parsed.netloc] = 0
        domains[parsed.netloc] += 1
        # count tags
        for tag in bkmk.tags:
            if tag not in tags:
                tags[tag] = 0
            tags[tag] += 1

    # print statistics
    if args.tag:
        tag_str = "\n".join(["{} : {}".format(x, y) for x,y in tags.items()])
        logging.info("Writing tag counts")
        with open('{}.tag_counts'.format(args.output), 'w') as f:
            f.write(tag_str)

        with open('{}.tags'.format(args.output), 'w') as f:
            f.write("\n".join([x for x in tags.keys()]))

    if args.domain:
        domain_str = "\n".join(["{} : {}".format(x,y) for x,y in domains.items()])
        logging.info("Domain Counts")
        with open('{}.domain_counts'.format(args.output), 'w') as f:
            f.write(domain_str)

        with open('{}.domains'.format(args.output), 'w') as f:
            f.write('\n'.join([x for x in domains.keys()]))
