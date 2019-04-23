"""
Split the bookmark library by top level domain
"""

# Setup root_logger:
from bkmkorg.io.import_netscape import open_and_extract_bookmarks
from bkmkorg.io.export_org import exportBookmarks as org_export
from os.path import splitext, split, abspath, exists, isdir, join
from os import mkdir
from urllib.parse import urlparse
import logging as root_logger
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
import argparse

parser = argparse.ArgumentParser("")
parser.add_argument('-l', '--library')
parser.add_argument('-s', '--source')
parser.add_argument('-o', '--output')

args = parser.parse_args()
args.source = abspath(expanduser(args.source))
args.library = abspath(expanduser(args.library))
args.output = abspath(expanduser(args.output))

if not isdir(args.output):
    logging.info("Making output Directory: {}".format(args.output))
    mkdir(args.output)

#load library
library = open_and_extract_bookmarks(args.library)

tags = {}

#process
logging.info("Grouping by tags")
for bkmk in library:
    for tag in bkmk.tags:
        if tag not in tags:
            tags[tag] = []
        tags[tag].append(bkmk)

#save
for tag, sites in tags.items():
    logging.info("Exporting: {}".format(tag))
    org_export(sites, join(args.output, "{}.org".format(tag)))
