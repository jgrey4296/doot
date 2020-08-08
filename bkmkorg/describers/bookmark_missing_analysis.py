"""
Compare source bookmark html's and txt's to a target library
Output an html and txt of bookmarks missing from that target library
"""
from bkmkorg.io.import_netscape import open_and_extract_bookmarks
from bkmkorg.io.export_netscape import exportBookmarks
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

    # Setup
    # see https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join(["Load a bookmark library and a number of -s(ources)",
                                                         "Output the bookmarks that are missing"]))
    parser.add_argument('-l', '--library', default="~/github/writing/other_files/main_bookmarks.html")
    parser.add_argument('-s', '--source', action='append')
    parser.add_argument('-o', '--output', default="~/Desktop/missing_bookmarks.html")

    args = parser.parse_args()
    args.library = abspath(expanduser(args.library))
    args.source = [abspath(expanduser(x)) for x in args.source]
    args.output = abspath(expanduser(args.output))
    logging.info("Finding Links missing from: {}".format(args.library))

    # Get sources
    sources = [x for x in args.source if isfile(x)]
    for x in [x for x in args.source if isdir(x)]:
        files = [join(x,y) for y in listdir(x) if splitext(y)[1] == '.html']
        sources += files

    logging.info("Using Source: {}".format(sources))

    #Load Library
    lib_list = open_and_extract_bookmarks(args.library)

    to_check = []
    to_check_raw = []

    #Load each specified source file
    for x in sources:
        if splitext(x)[1] == ".html":
            to_check += open_and_extract_bookmarks(x)
        elif splitext(x)[1] == ".txt":
            with open(x, 'r') as f:
                to_check_raw += [l.strip() for l in f.readlines() if l.strip() != ""]

    logging.info("Total Links to Check: {}".format(len(to_check)))

    # Get links that don't match *exactly*, use hash first,
    # if hash exists, compare exactly
    lookup = {x.url : x for x in lib_list}
    missing = []
    for x in to_check:
        if x.url not in lookup:
            missing.append(x)

    missing_raw = []
    for x in to_check_raw:
        if x not in lookup:
            missing_raw.append(x)

    #write missing out to separate files
    exportBookmarks(missing, args.output)

    if bool(missing_raw):
        with open("{}.txt".format(splitext(args.output)[0]), 'w') as f:
            f.write("\n".join(missing_raw))
