#!/opt/anaconda3/envs/bookmark/bin/python

from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir
import argparse
import re
from collections import defaultdict

from bkmkorg.utils.file.retrieval import get_data_files

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
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog = "\n".join(["Index all tags found in orgs"]))
parser.add_argument('--target', action="append")
parser.add_argument('--output')

TAG_LINE = re.compile(r'^\*\* Thread: .+?\s{5,}:(.+?):$')

if __name__ == '__main__':
    logging.info("---------- STARTING Tag Indexer")
    args = parser.parse_args()
    args.target = [abspath(expanduser(x)) for x in args.target]
    args.output = abspath(expanduser(args.output))

    targets = get_data_files(args.target, ext=".org")

    total_index = defaultdict(lambda: set())

    for filename in targets:
        # read in
        lines = []
        with open(filename, 'r') as f:
            lines = f.readlines()

        # headlines with tags
        matched = [TAG_LINE.match(x) for x in lines]
        actual = [x for x in matched if bool(x)]
        tags    = [y for x in actual for y in x[1].split(":") if bool(x)]
        # add to index
        for tag in tags:
            total_index[tag].add(filename)

    # Write out index
    items = list(total_index.items())
    items.sort(key=lambda x: x[0])
    out_lines = ["{} :{}".format(x, ":".join(y)) for x,y in items]
    out_string = "\n".join(out_lines)
    with open(args.output, 'w') as f:
        f.write(out_string)
