"""
Generates an org file from loaded bookmarks,
of weblinks with and without each unique html paramter

This is intended for testing to determine which
parameters can be filtered out
Pairs with bkmkorg/filters/bookmark_param_filter
"""
##-- imports
from __future__ import annotations

import argparse
import logging as root_logger
import pathlib as pl
from urllib.parse import urlparse

from bkmkorg.bibtex import parsing as BU
from bkmkorg.bookmarks.collection import BookmarkCollection
from bkmkorg.files import collect
##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.path(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##-- end logging

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["For a bookmark file",
                                                        "Create an org file of paired links",
                                                        "which compare the original link",
                                                        "with the link minus an html parameter"]))
parser.add_argument('-l', '--library', required=True)
parser.add_argument('-o', '--output', required=True)

##-- end argparse


##-- ifmain
if __name__ == "__main__":
    args         = parser.parse_args()
    args.library = pl.Path(args.library).expanduser().resolve()
    args.output  = pl.Path(args.output).expanduser().resolve()

    assert(args.library.exists())

    # Load the library
    logging.info("Loading Library")
    lib_files = collect.get_data_files(args.library, ".bookmarks")
    library = BookmarkCollection()
    for bkmk_f in lib_files:
        with open(bkmk_f, 'r') as f:
            library.add_file(f)

    logging.info("Processing Library")
    # TODO Generate org file
    # org_str = the_trie.org_format_queries()
    # with open("{}.org".format(args.output), 'w') as f:
        # f.write(org_str)

##-- end ifmain
