"""
Merge duplicate url'd bookmarks together
"""
import argparse
import logging as root_logger
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

from bkmkorg.utils.bookmarks.collection import Bookmark, BookmarkCollection
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval

# Setup root_logger:
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Remove Duplicates (by full url) from a bookmark file, merging tags"]))
parser.add_argument('-s', '--source', required=True)
parser.add_argument('-o', '--output', default="~/Desktop/deduplicated_bookmarks.html")


if __name__ == "__main__":
    args = parser.parse_args()
    args.output = abspath(expanduser(args.output))

    logging.info("Deduplicating {}".format(args.source))
    source_files = retrieval.get_data_files(args.source, ".bookmarks")
    total = BookmarkCollection()
    for bkmk_f in source_files:
        with open(bkmk_f, 'r') as f:
            total.add_file(f)

    logging.info("Total Links to Check: {}".format(len(total)))

    total.merge_duplicates()

    logging.info("Final Number of Links: {}".format(len(total)))
    #write out to separate file
    with open(args.output, 'w') as f:
        f.write(str(total))
