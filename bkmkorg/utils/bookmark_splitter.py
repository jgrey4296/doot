"""
Splits a bookmark file into subfiles by url
"""

from os.path import splitext, split, exists, expanduser, abspath, isdir, join
from os import mkdir
from bkmkorg.io.import_netscape import open_and_extract_bookmarks
from bkmkorg.io.export_netscape import exportBookmarks
import logging as root_logger
from urllib.parse import urlparse
import argparse
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Split bookmarks into separate files by url netloc"]))
parser.add_argument('-s', '--source')
parser.add_argument('-o', '--output')

args = parser.parse_args()
args.source = abspath(expanduser(args.source))
args.output = abspath(expanduser(args.output))

assert(exists(args.source))

mkdir(args.output)

# Load the library
logging.info("Loading Source")
source = open_and_extract_bookmarks(args.source)

domains = {}

logging.info("Processing Library")
for bkmk in source:
    # Count websites
    parsed = urlparse(bkmk.url)
    if parsed.netloc not in domains:
        domains[parsed.netloc] = []
    domains[parsed.netloc].append(bkmk)

# print statistics
logging.info("Writing Domain Files")
for domain, bkmks in domains.items():
    exportBookmarks(bkmks, join(args.output, "{}.html".format(domain)))
