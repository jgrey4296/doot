"""
Integrate new bookmarks into the main bookmark file
"""
import argparse
from bkmkorg.io.import_netscape import open_and_extract_bookmarks
from bkmkorg.io.export_org import exportBookmarks as org_export
from bkmkorg.io.export_netscape import exportBookmarks as html_export
# Setup root_logger:
from os.path import splitext, split, exists, expanduser, abspath
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
                                 epilog = "\n".join(["Find all bookmarks in {source} files and create a master {output} html"]))
parser.add_argument('-s', '--sources', action='append')
parser.add_argument('-o', '--output')

args = parser.parse_args()
args.sources = [abspath(expanduser(x)) for x in args.sources]

assert(all([exists(x) for x in args.sources]))

if splitext(args.output)[1] != ".html":
    raise Exception("Html not specified for output")

if exists(args.output):
    logging.warning("Ouput already exists: {}".format(args.output))
    response = input("Overwrite? Y/*: ")
    if response != "Y":
        logging.info("Cancelling")
        exit()

#load the sources
bkmk_dict = {}

for loc in args.sources:
    logging.info("Dict Length: {}".format(len(bkmk_dict)))
    logging.info("Opening: {}".format(loc))
    source_bkmks = open_and_extract_bookmarks(loc)
    for x in source_bkmks:
        #combine without duplicating
        if x.url not in bkmk_dict:
            bkmk_dict[x.url] = x
            continue
        bkmk_dict[x.url].tags.update(x.tags)

logging.info("Writing out: {}".format(len(bkmk_dict)))
#write out
html_export(list(bkmk_dict.values()), args.output)
