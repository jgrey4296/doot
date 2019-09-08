"""
Generates an org file from loaded bookmarks,
of weblinks with and without each unique html paramter

This is intended for testing to determine which
parameters can be filtered out
Pairs with bkmkorg/filters/bookmark_param_filter
"""

from bkmkorg.io.import_netscape import open_and_extract_bookmarks
from bkmkorg.utils.trie import Trie
from os.path import splitext, split, exists, expanduser, abspath
from urllib.parse import urlparse
import argparse
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["For a bookmark file",
                                                     "Create an org file of paired links",
                                                     "which compare the original link",
                                                     "with the link minus an html parameter"]))
parser.add_argument('-l', '--library')
parser.add_argument('-o', '--output')

args = parser.parse_args()
args.library = abspath(expanduser(args.library))
args.output = abspath(expanduser(args.output))

assert(exists(args.library))

# Load the library
logging.info("Loading Library")
library = open_and_extract_bookmarks(args.library)

logging.info("Processing Library")
the_trie = Trie(library)

org_str = the_trie.org_format_queries()

with open("{}.org".format(args.output), 'w') as f:
    f.write(org_str)
