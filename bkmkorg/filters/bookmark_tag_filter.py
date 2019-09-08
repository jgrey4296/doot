"""
Process all bookmarks and filter out / substitute based on input list
Pairs with bkmkorg/describers/bookmark_tag_domain.py
"""
# Setup root_logger:
import IPython
import argparse
from bkmkorg.io.import_netscape import open_and_extract_bookmarks
from bkmkorg.io.export_netscape import exportBookmarks as html_export
from bkmkorg.io.export_org import exportBookmarks as org_export
from os.path import splitext, split, join, exists, expanduser, abspath, isdir
from os import listdir
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
                                 epilog="\n".join(["Load bookmarks, filter and substitute tags",
                                                   "-f {file} a newline list of tags to remove",
                                                   "-s {file} a newline list of colon separated pairs",
                                                   "Pairs with bkmkorg/describers/bookmark_tag_domain.py"]))
parser.add_argument('-l', '--library')
parser.add_argument('-s', '--source', default=None)
parser.add_argument('-o', '--output')

args = parser.parse_args()
if args.source:
    args.source = abspath(expanduser(args.source))
args.library = abspath(expanduser(args.library))
args.output = abspath(expanduser(args.output))

assert(exists(args.library))

#load library
logging.info("Loading Library")
library = open_and_extract_bookmarks(args.library)

master_dict = {}
filter_set = set()
sub_set = set()

if args.source and exists(args.source):
    sources = [args.source]
    if isdir(args.source):
        sources = [join(args.source, x) for x in listdir(args.source) if splitext(x)[1] == ".org"]

    logging.info("Loading Sources: {}".format(len(sources)))
    for source_file in sources:
        with open(source_file, 'r') as f:
            lines = f.read().split('\n')
        applicable_lines = [x for x in lines if bool(x) and x[0] != "*"]
        split_lines = [x.split(':') for x in applicable_lines]
        if any([len(x) > 2 for x in split_lines]):
            IPython.embed(simple_prompt=True)

        master_dict.update({x[0].strip() : x[1].strip() for x in split_lines})

    filter_set = {x for x, y in master_dict.items() if y == "__filter__"}
    sub_set = {x for x, y in master_dict.items() if y not in ("__filter__", "__leave__")}

logging.info("Performing filter and sub")
for bkmk in library:
    bkmk.tags.difference_update(filter_set)
    inter = bkmk.tags.intersection(sub_set)
    bkmk.tags.difference_update(inter)
    bkmk.tags.update([master_dict[x] for x in inter])

logging.info("Saving library")
html_export(library, "{}.html".format(args.output))
