#!/usr/bin/env python3

"""
Indexer for bibtex tags -> files
"""
import argparse
##############################
# IMPORTS
####################
import logging as root_logger
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)

import bibtexparser as bib
import bkmkorg.utils.bibtex.parsing as bib_parse
import bkmkorg.utils.dfs.files as RET
from bkmkorg.utils.bibtex import entry_processors as bib_proc
from bkmkorg.utils.indices.collection import IndexFile

# Setup root_logger:
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################

def main():
    #see https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                   epilog = "\n".join(["Bibtex Tag Indexer"]))
    parser.add_argument('--target', action="append")
    parser.add_argument('--output', default="~/github/writing/resources/cron_reports/tag_bibtex.index")

    args = parser.parse_args()
    if not bool(args.target):
        args.target = ["/Volumes/documents/github/writing/resources/bibliography"]

    bibs = RET.collect_files(args.target)[0]

    # Load bibs
    db = bib_parse.parse_bib_files(bibs, func=bib_proc.tags)

    # map to tags
    index = IndexFile()
    for entry in db.entries:
        for tag in entry['tags']:
            # TODO get all the `file[digit]` keys
            if 'file' in entry:
                index.add_files(tag, entry['file'])


    # Write out index
    out_string = str(index)
    with open(abspath(expanduser(args.output)), 'w') as f:
        f.write(out_string)

########################################
if __name__ == "__main__":
    main()
