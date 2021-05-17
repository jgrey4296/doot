"""
Merge duplicate url'd bookmarks together
"""
import argparse
import logging as root_logger
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

from bkmkorg.utils.bookmark.bookmark_data import bookmarkTuple
from bkmkorg.io.export.export_netscape import exportBookmarks
from bkmkorg.io.import.import_netscape import open_and_extract_bookmarks
from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.file import retrieval

if __name__ == "__main__":
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
    parser.add_argument('-s', '--source')
    parser.add_argument('-o', '--output', default="~/Desktop/deduplicated_bookmarks.html")

    args = parser.parse_args()
    args.output = abspath(expanduser(args.output))

    logging.info("Deduplicating {}".format(args.source))
    source_files = retrieval.get_data_files(args.source, ".html")
    to_check = [y for x in source_files for y in open_and_extract_bookmarks(x)]

    logging.info("Total Links to Check: {}".format(len(to_check)))

    #Get links that don't match *exactly*, use hash first,
    #if hash exists, compare exactly
    deduplicated = {}
    for x in to_check:
        if x.url not in deduplicated:
            deduplicated[x.url] = x
        else:
            combined_tags = set()
            combined_tags.update(x.tags)
            combined_tags.update(deduplicated[x.url].tags)
            deduplicated[x.url] = bookmarkTuple(x.name, x.url, combined_tags)

    logging.info("Final Number of Links: {}".format(len(deduplicated)))
    #write out to separate file
    exportBookmarks([x for x in deduplicated.values()], args.output)
