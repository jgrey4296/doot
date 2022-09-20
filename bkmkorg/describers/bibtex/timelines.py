#!/usr/bin/env python
##-- imports
import argparse
import logging as root_logger
from collections import defaultdict
from datetime import datetime
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import pathlib as pl
import bibtexparser as b
from bibtexparser import customization as c

from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.bibtex import entry_processors as bib_proc
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils.collections.timeline import TimelineFile

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
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Create Timelines for Bibtex Files"]))
parser.add_argument('--library', action="append", required=True)
parser.add_argument('--min_entries', default=5, type=int)
parser.add_argument('--output', required=True)
##-- end argparse

def main():
    args = parser.parse_args()
    args.library = [pl.Path(x).expanduser().resolve() for x in args.library]
    args.output  = pl.Path(args.output).expanduser().resolve()
    assert(args.output.is_dir())
    logging.info("---------- STARTING Bibtex Timelines")
    if not args.output.exists():
        logging.info("Making output: %s", args.output)
        args.output.mkdir()

    assert(args.output.exists())

    all_bibs = retrieval.get_data_files(args.library, ".bib")

    logging.info("Found %s bib files", len(all_bibs))

    db = b.bibdatabase.BibDatabase()
    BU.parse_bib_files(all_bibs, func=bib_proc.year_parse, database=db)

    logging.info("Loaded bibtex entries: %s", len(db.entries))

    # Load totals_bib.tags
    # Filter for min_entries

    # Create a TimelineFile for each tag
    # Add citations to each tag TimelineFile
    # Write out timeline files

    tag_collection = defaultdict(list)
    for entry in db.entries:
        tags = entry['tags']
        for tag in tags:
            tag_collection[tag].append(entry)

    logging.info("Collected Tags: %s", len(tag_collection))

    # Then sort by year and write out
    for tag, entries in tag_collection.items():
        out_target = args.output / "{}.tag_timeline".format(tag)
        sorted_entries = sorted(entries, key=lambda x: x['year'])

        if len(sorted_entries) > args.min_entries:
            with open(out_target, 'w') as f:
                f.write("\n".join(["{} {}".format(x['year'].strftime("%Y"), x['ID']) for x in sorted_entries]))


if __name__ == "__main__":
    main()
