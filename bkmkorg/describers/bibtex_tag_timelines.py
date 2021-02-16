#!/usr/bin/env python3

from typing import Callable, Iterator, Union, Match
from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

import argparse
import logging as root_logger
from collections import defaultdict
from datetime import datetime

from bibtexparser import customization as c
from bibtexparser.bparser import BibTexParser
import bibtexparser as b

from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir, mkdir

from bkmkorg.utils import retrieval
from bkmkorg.utils import bibtex as BU

# Setup root_logger:
LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################

def custom_parse(record):
    if 'year' not in record:
        year_temp = "2020"
    else:
        year_temp = record['year']
    if "/" in year_temp:
        year_temp = year_temp.split("/")[0]

    year = datetime.strptime(year_temp, "%Y")
    tags = []
    if 'tags' in record:
        tags = [x.strip() for x in record['tags'].split(",")]

    record['year'] = year
    record['tags'] = tags

    return record



if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join(["Create Timelines for Bibtex Files"]))
    parser.add_argument('--library', action="append")
    parser.add_argument('--target')

    args = parser.parse_args()
    args.library = [abspath(expanduser(x)) for x in args.library]
    args.target = abspath(expanduser(args.target))
    if not exists(args.target):
        logging.info("Making target: {}".format(args.target))
        mkdir(args.target)

    assert(exists(args.target))

    all_bibs = retrieval.get_data_files(args.library, ".bib")

    logging.info("Found {} bib files".format(len(all_bibs)))

    db = b.bibdatabase.BibDatabase()
    BU.parse_bib_files(all_bibs, func=custom_parse, database=db)

    logging.info("Loaded bibtex entries: {}".format(len(db.entries)))

    tag_collection = defaultdict(list)
    for i, entry in enumerate(db.entries):
        tags = entry['tags']
        for tag in tags:
            tag_collection[tag].append(entry)

    logging.info("Collected Tags: {}".format(len(tag_collection)))

    # Then sort by year and write out
    for tag, entries in tag_collection.items():
        out_target = join(args.target, "{}.tag_timeline".format(tag))
        sorted_entries = sorted(entries, key=lambda x: x['year'])

        with open(out_target, 'w') as f:
            f.write("\n".join(["{} {}".format(x['year'].strftime("%Y"), x['ID']) for x in sorted_entries]))
