"""
Process all bookmarks and filter out / substitute based on input list
"""
# Setup root_logger:
from bkmkorg.io.import_netscape import open_and_extract_bookmarks
from export_netscape import exportBookmarks as html_export
from export_org import exportBookmarks as org_export
from os.path import splitext, split, join, exists, expanduser, abspath
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

#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser("")
parser.add_argument('-l', '--library')
parser.add_argument('-f', '--filter', default=None)
parser.add_argument('-s', '--sub', default=None)
parser.add_argument('-o', '--output')

args = parser.parse_args()
if args.filter:
    args.filter = abspath(expanduser(args.filter))
if args.sub:
    args.sub = abspath(expanduser(args.sub))
args.library = abspath(expanduser(args.library))
args.output = abspath(expanduser(args.output))

assert(exists(args.library))

#load library
logging.info("Loading Library")
library = open_and_extract_bookmarks(args.library)

if args.filter:
    logging.info("Filtering Tags")
    filter_list = None
    with open(args.filter, 'r') as f:
        filter_list = set([x.strip() for x in f.read().split('\n')])
    assert(filter_list is not None)
    logging.info("Filtering {} tags".format(len(filter_list)))
    for bkmk in library:
        bkmk.tags.difference_update(filter_list)

if args.sub:
    logging.info("Substituting Tags")
    sub_list = {}
    with open(args.sub, 'r') as f:
        sub_text = f.read().split('\n')
    for line in sub_text:
        existing, replacement = [x.strip() for x in line.split(":")]
        assert(existing not in sub_list)
        sub_list[existing] = replacement
    logging.info("Substituting {} tags".format(len(sub_list)))
    for bkmk in library:
        for tag in bkmk.tags:
            if tag in sub_list:
                bkmk.tags.remove(tag)
                bkmk.tags.add(sub_list[tag])

#save
if args.filter or args.sub:
    logging.info("Saving library")
    html_export(library, "{}.html".format(args.output))
    org_export(library, "{}.org".format(args.output))
