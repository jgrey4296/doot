from bkmkorg.io.import_netscape import open_and_extract_bookmarks
from bkmkorg.io.export_netscape import exportBookmarks
import argparse
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir
# Setup root_logger:
from os.path import splitext, split
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".joing(["Load a bookmark library and a number of -s(ources)",
                                                      "Output the bookmarks that are missing"]))
parser.add_argument('-l', '--library', default="~/github/writing/other_files/main_bookmarks.html")
parser.add_argument('-s', '--source', action='append')
parser.add_argument('-o', '--output', default="~/Desktop/missing_bookmarks.html")

args = parser.parse_args()
args.library = abspath(expanduser(args.library))
args.source = [abspath(expanduser(x)) for x in args.source]
args.output = abspath(expanduser(args.output))
logging.info("Finding Links missing from: {}".format(args.library))

sources = [x for x in args.source if isfile(x)]
for x in [x for x in args.source if isdir(x)]:
    files = [join(x,y) for y in listdir(x) if splitext(y)[1] == '.html']
    sources += files

logging.info("Using Source: {}".format(sources))

#Load Library
lib_list = open_and_extract_bookmarks(args.library)

#Load each specified file
to_check = []
for x in sources:
    to_check += open_and_extract_bookmarks(x)

logging.info("Total Links to Check: {}".format(len(to_check)))

#Get links that don't match *exactly*, use hash first,
#if hash exists, compare exactly
lookup = {x.url : x for x in lib_list}
missing = []
for x in to_check:
    if x.url not in lookup:
        missing.append(x)


#write out to separate file
exportBookmarks(missing, args.output)
