#!/usr/bin/env python3
"""
Split the bookmark source by top level domain
"""

import argparse
import logging as root_logger
from os import mkdir
from os.path import abspath, exists, expanduser, isdir, join, split, splitext
from urllib.parse import urlparse
from collections import defaultdict
import re

from bkmkorg.utils.dfs.files import get_data_files

# Setup
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Load a bookmark file, split into url netlocs"]))
parser.add_argument('-s', '--source', action="append")
parser.add_argument('-o', '--output')

CLEAN = re.compile(r"^www\.")


def main():
    args = parser.parse_args()
    args.output = abspath(expanduser(args.output))

    assert(isdir(args.output) or not exists(args.output))
    if not exists(args.output):
        mkdir(args.output)

    if not isdir(args.output):
        mkdir(args.output)

    # load source
    lib_files = get_data_files(args.source, ext=".bookmarks")
    library = BookmarkCollection()
    for bkmk_f in lib_files:
        with open(bkmk_f, 'r') as f:
            library.add_file(f)

    domains      = defaultdict(lambda: [])

    # Group urls into domains
    for bkmk in library:
        parsed = urlparse(bkmk.url)

        netloc = CLEAN.sub("", parsed.netloc)

        if "github" in netloc:
            domains["github"].append(bkmk)
        elif "itch.io" in netloc:
            domains["itchio"].append(bkmk)
        else:
            domains[netloc].append(bkmk)

    logging.info(f"Grouped into {len(domains)} domains")
    #save
    groups = "\n".join(domains.keys())
    with open(join(args.output, "netlocs.list"), 'w') as f:
        f.write(groups)

    for domain, bkmks in domains.items():
        flattened = domain.replace(".", "_")
        bkmks_s = "\n".join([str(x) for x in sorted(bkmks)])
        with open(join(args.output, f"{flattened}.bookmarks"), 'w') as f:
            f.write(bkmks_s)



if __name__ == "__main__":
    main()
