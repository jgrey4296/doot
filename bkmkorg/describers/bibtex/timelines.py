#!/opt/anaconda3/envs/bookmark/bin/python
import argparse
import logging as root_logger
from collections import defaultdict
from datetime import datetime
from os import listdir, mkdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import bibtexparser as b
from bibtexparser import customization as c

from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.file import retrieval

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
    parser.add_argument('--min_entries', default=5, type=int)
    parser.add_argument('--output')

    args = parser.parse_args()
    args.library = [abspath(expanduser(x)) for x in args.library]
    args.output= abspath(expanduser(args.output))
    logging.info("---------- STARTING Bibtex Timelines")
    if not exists(args.output):
        logging.info("Making output: {}".format(args.output))
        mkdir(args.output)

    assert(exists(args.output))

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
        out_target = join(args.output, "{}.tag_timeline".format(tag))
        sorted_entries = sorted(entries, key=lambda x: x['year'])

        if len(sorted_entries) > args.min_entries:
            with open(out_target, 'w') as f:
                f.write("\n".join(["{} {}".format(x['year'].strftime("%Y"), x['ID']) for x in sorted_entries]))
