#!/usr/bin/env python
##-- imports
from __future__ import annotations

import argparse
import json
import logging as root_logger
import pathlib as pl
import re

from bkmkorg.bibtex import parsing as BU
from bkmkorg.files import collect
from bkmkorg.org.links import map_media, make_relative_media_links
##-- end imports

##-- logging
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(pl.Path(__file__).stem)
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##-- end logging

##-- consts
DEFAULT_PATTERN = re.compile(r"(.*?\[+)/Users/johngrey/Desktop/twitter/orgs/(.+?)(\]\[.+)$")
PERMALINK       = re.compile(r".*?:PERMALINK: *\[\[(.+?)\]\[")
LINK            = re.compile(r".*\[\[(.+?)\]\[")
##-- end consts

##-- argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join([""]))
parser.add_argument('--target', action="append", required=True)
parser.add_argument('--media', required=True)
parser.add_argument('--pattern', default=DEFAULT_PATTERN)
##-- end argparse

def main():
    my_args = parser.parse_args()
    my_args.media = pl.Path(my_args.media).expanduser().resolve()
    my_args.pattern = re.compile(my_args.pattern)

    # find all orgs
    orgs = collect.get_data_files(my_args.target, ".org")
    found_media = {}
    logging.info("Found: %s orgs", len(orgs))
    for org in orgs:
        make_relative_media_links(org, my_args.pattern)
        found_media.update(map_media(org))

    with open(my_args.media, 'w') as f:
        json.dump(found_media, f)

    # Media:
    # Get exiftool data,
    # Compare distance of creation time, X Y Ratio, duration
    # move similars into separate folder, note its source and similarities


##-- ifmain
if __name__ == "__main__":
    main()
##-- end ifmain
