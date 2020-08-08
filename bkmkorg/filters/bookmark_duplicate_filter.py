"""
Merge duplicate url'd bookmarks together
"""
from bkmkorg.io.import_netscape import open_and_extract_bookmarks
from bkmkorg.io.export_netscape import exportBookmarks
from bkmkorg.bookmark_data import bookmarkTuple
import argparse
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir
from os.path import splitext, split
import logging as root_logger

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
    args.source = abspath(expanduser(args.source))
    args.output = abspath(expanduser(args.output))

    logging.info("Deduplicating {}".format(args.source))
    to_check = open_and_extract_bookmarks(args.source)

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
