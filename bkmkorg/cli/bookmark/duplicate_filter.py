"""
Merge duplicate url'd bookmarks together
"""
##-- imports
from __future__ import annotations

import argparse
import logging as root_logger
import pathlib as pl

from bkmkorg.bibtex import parsing as BU
from bkmkorg.bookmarks.collection import Bookmark, BookmarkCollection
from bkmkorg.files import collect

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
                                    epilog = "\n".join(["Remove Duplicates (by full url) from a bookmark file, merging tags"]))
parser.add_argument('-s', '--source', required=True)
parser.add_argument('-o', '--output', default="~/Desktop/deduplicated_bookmarks.html")
##-- end argparse


##-- ifmain
if __name__ == "__main__":
    args = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()

    logging.info("Deduplicating %s", args.source)
    source_files = collect.get_data_files(args.source, ".bookmarks")
    total = BookmarkCollection()
    for bkmk_f in source_files:
        with open(bkmk_f, 'r') as f:
            total.add_file(f)

    logging.info("Total Links to Check: %s", len(total))

    total.merge_duplicates()

    logging.info("Final Number of Links: %s", len(total))
    #write out to separate file
    with open(args.output, 'w') as f:
        f.write(str(total))

##-- end ifmain
