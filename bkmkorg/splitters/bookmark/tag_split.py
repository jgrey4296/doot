"""
Split the bookmark library by top level domain
"""

import argparse
import logging as root_logger
from os import mkdir
from os.path import abspath, exists, isdir, join, split, splitext, expanduser
from urllib.parse import urlparse
from bkmkorg.utils.bookmarks.collection import BookmarkCollection

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
parser.add_argument('-l', '--library', required=True)
parser.add_argument('-o', '--output', required=True)


if __name__ == "__main__":
    args = parser.parse_args()
    args.library = abspath(expanduser(args.library))
    args.output = abspath(expanduser(args.output))

    if not isdir(args.output):
        logging.info("Making output Directory: {}".format(args.output))
        mkdir(args.output)

    # load library
    lib_files = retrieval.get_data_files(args.library, ".html")
    library = BookmarkCollection()
    for bkmk_f in lib_files:
        with open(bkmk_f, 'r') as f:
            library.add_file(f)

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
        # TODO org_export(sites, join(args.output, "{}.org".format(tag)))
