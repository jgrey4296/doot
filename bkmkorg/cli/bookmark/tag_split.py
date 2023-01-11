"""
Split the bookmark library by top level domain
"""
##-- imports
from __future__ import annotations

import argparse
import logging as root_logger
import pathlib as pl
from urllib.parse import urlparse

from bkmkorg.bookmarks.collection import BookmarkCollection
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
                                    epilog = "\n".join(["Read a bookmark file, split it into separate files by tag"]))
parser.add_argument('-l', '--library', required=True)
parser.add_argument('-o', '--output', required=True)
##-- end argparse


##-- ifmain
if __name__ == "__main__":
    args         = parser.parse_args()
    args.library = pl.Path(args.library).expanduser().resolve()
    args.output  = pl.Path(args.output).expanduser().resolve()

    if not args.output.is_dir():
        logging.info("Making output Directory: %s", args.output)
        args.output.mkdir()

    # load library
    lib_files = retrieval.get_data_files(args.library, ".html")
    library   = BookmarkCollection()
    for bkmk_f in lib_files:
        library.add_file(bkmk_f)

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
        logging.info("Exporting: %s", tag)
        # TODO org_export(sites, join(args.output, "{}.org".format(tag)))

##-- end ifmain
