"""
Stat generator for bookmarks
Pairs with bkmkorg/filters/bookmark_tag_filter
"""

##-- imports
from __future__ import annotations
import argparse
import logging as root_logger
from urllib.parse import urlparse
from collections import defaultdict

import pathlib as pl
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.bookmarks.collection import BookmarkCollection
from bkmkorg.utils.tag.collection import TagFile
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
                                epilog = "\n".join(["For a bookmark file, print out domain counts and tag counts",
                                                    "Pairs with bkmkorg/filters/bookmark_tag_filter"]))
parser.add_argument('-l', '--library', required=True)
parser.add_argument('-o', '--output', required=True)
parser.add_argument('-d', '--domain', action="store_true")
##-- end argparse


if __name__ == "__main__":
    args         = parser.parse_args()
    args.library = pl.Path(args.library).expanduser().resolve()
    args.output  = pl.Path(args.output).expanduser().resolve()

    assert(args.library.exists())

    # Load the library
    logging.info("Loading Library")
    library   = BookmarkCollection()
    lib_files = retrieval.get_data_files(args.library, ".html")
    for lib_f in lib_files:
        with open(lib_f, 'r') as f:
            library.add_file(f)

    domains = TagFile()

    # Process library for tags and domains
    logging.info("Processing Library")
    for bkmk in library:
        # Count websites
        parsed = bkmk.url_comps
        domains.inc(parsed.netloc)

    logging.info("Domain Counts")
    with open(f'{args.output}.domain_counts', 'w') as f:
        f.write(str(domains))
