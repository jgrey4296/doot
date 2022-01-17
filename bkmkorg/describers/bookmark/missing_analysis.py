"""
Compare source bookmark html's and txt's to a target library
Output an html and txt of bookmarks missing from that target library
"""
import argparse
import logging as root_logger
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.bookmarks.collection import BookmarkCollection
#
# Setup root_logger:
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)

# Setup
# see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Load a bookmark library and a number of -s(ources)",
                                                        "Output the bookmarks that are missing"]))
parser.add_argument('-l', '--library', default="~/github/writing/other_files/main_bookmarks.html")
parser.add_argument('-s', '--source', action='append')
parser.add_argument('-o', '--output', default="~/Desktop/missing_bookmarks.html")


if __name__ == "__main__":
    args         = parser.parse_args()
    args.library = abspath(expanduser(args.library))
    args.source  = [abspath(expanduser(x)) for x in args.source]
    args.output  = abspath(expanduser(args.output))
    logging.info("Finding Links missing from: {}".format(args.library))

    # Get sources
    sources = retrieval.get_data_files(args.source, [".bookmarks"])
    logging.info("Using Source: {}".format(sources))

    #Load Library
    library_files = retrieval.get_data_files(args.library, ".bookmarks")
    library : BookmarkCollection = BookmarkCollection()
    for bkmk_f in library_files:
        with open(bkmk_f, 'r') as f:
            library.add_file(f)

    to_check = BookmarkColleciton()
    #Load each specified source file
    for x in sources:
        with open(x, 'r') as f:
            to_check.add_file(f)

    logging.info("Total Links to Check: {}".format(len(to_check)))

    missing : BookmarkCollection = library.difference(to_check)

    if bool(missing):
        with open("{}.bookmarks".format(splitext(args.output)[0]), 'w') as f:
            f.write(str(missing))
