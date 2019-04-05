"""
Stat generator for bookmarks
"""

# Setup root_logger:
from os.path import splitext, split, exists, expanduser, abspath
from html_opener import open_and_extract_bookmarks
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

parser = argparse.ArgumentParser("")
parser.add_argument('-l', '--library')
parser.add_argument('-o', '--output')

args = parser.parse_args()
args.library = abspath(expanduser(args.library))
args.output = abspath(expanduser(args.output))

assert(exists(args.library))

# Load the library
logging.info("Loading Library")
library = open_and_extract_bookmarks(args.library)

tags = {}
domains = {}

logging.info("Processing Library")
for bkmk in library:
    # Count websites
    parsed = urlparse(bkmk.url)
    if parsed.netloc not in domains:
        domains[parsed.netloc] = 0
    domains[parsed.netloc] += 1
    # count tags
    for tag in bkmk.tags:
        if tag not in tags:
            tags[tag] = 0
        tags[tag] += 1


# print statistics
tag_str = "\n".join(["{} : {}".format(x, y) for x,y in tags.items()])
domain_str = "\n".join(["{} : {}".format(x,y) for x,y in domains.items()])
logging.info("Writing tag counts")
with open('{}.tags'.format(args.output), 'w') as f:
    f.write(tag_str)

logging.info("Domain Counts")
with open('{}.domains'.format(args.output), 'w') as f:
    f.write(domain_str)
