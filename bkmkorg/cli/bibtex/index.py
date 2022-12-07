#!/usr/bin/env python3

"""
Indexer for bibtex tags -> files
"""
##-- imports
from __future__ import annotations
import argparse
import logging as root_logger

import pathlib as pl
import bibtexparser as bib
import bkmkorg.bibtex.parsing as bib_parse
import bkmkorg.files.collect as RET
from bkmkorg.bibtex import entry_processors as bib_proc
from bkmkorg.collections.indexfile import IndexFile
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

##-- argparse
#see https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog = "\n".join(["Bibtex Tag Indexer"]))
parser.add_argument('--target', action="append", required=True)
parser.add_argument('--output', default="~/github/writing/resources/cron_reports/tag_bibtex.index")
##-- end argparse

def main():
    args = parser.parse_args()
    args.output = pl.Path(args.output).expanduser().resolve()

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
    with open(args.output, 'w') as f:
        f.write(out_string)

########################################
##-- ifmain
if __name__ == "__main__":
    main()

##-- end ifmain
