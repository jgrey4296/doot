#!/usr/bin/env python
# load bibtex, graph tags by year, all entries by year,

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
from bibtexparser.bparser import BibTexParser
from matplotlib import pyplot as plt

from bkmkorg.utils.bibtex import parsing as BU
from bkmkorg.utils.bibtex import entry_processors as bib_proc
from bkmkorg.utils.dfs import files as retrieval
from bkmkorg.utils import diagram as DU
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

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog = "\n".join(["Create graphs of Bibtex Files"]))
parser.add_argument('-l', '--library', action="append", help="The bibtex file collection directory", required=True)
parser.add_argument('-o', '--output', help="The output target directory", required=True)
parser.add_argument('-t', '--tag', help="Optional Focus Tag")



def get_tag_across_years(db, tag) -> List[Tuple[datetime, int]]:
    """
    Find the earliest instance of the tag,
    then track counts from that year onwards
    """
    results_dict : Dict[datetime, int] = defaultdict(lambda: 0)
    for entry in db.entries:
        year = entry['year']
        if tag in entry['tags']:
            results_dict[year] += 1


    return sorted(results_dict.items(), key=lambda x: x[0])

def get_entries_across_years(db) -> List[Tuple[datetime, int]]:
    results_dict : Dict[datetime, int] = defaultdict(lambda: 0)
    for entry in db.entries:
        year = entry['year']
        results_dict[year] += 1

    return sorted(results_dict.items(), key=lambda x: x[0])


def main():
    args         = parser.parse_args()
    args.library = [pl.Path(x).expanduser().resolve() for x in args.library]
    args.output  = pl.Path(args.output).expanduser().resolve()

    all_bibs = retrieval.get_data_files(args.library, ".bib")
    logging.info("Found %s bib files", len(all_bibs))
    db = b.bibdatabase.BibDatabase()
    BU.parse_bib_files(all_bibs, func=bib_proc.year_parse, database=db)
    logging.info("Loaded bibtex entries: %s", len(db.entries))

    # Graph tags over time
    year_counts = []
    if args.tag:
        year_counts = get_tag_across_years(db, args.tag)
    else:
        year_counts: List[Tuple[datetime, int]] = get_entries_across_years(db)

    year_counts = [x for x in year_counts if x[1] > 5]
    # chart the tweets
    to_draw = [("Years", year_counts)]
    # n_rows = int(len(to_draw) / 2)
    # n_cols = int(len(to_draw) / 2)
    n_rows = 1
    n_cols = 1
    for count, paired in enumerate(to_draw):
        name, data = paired
        logging.info("Drawing %s", name)
        x = [x[0] for x in data]
        y = [x[1] for x in data]
        plt.subplot(n_rows, n_cols, count + 1)
        plt.scatter(x, y, alpha=0.3)
        plt.title(name)
        plt.gcf().autofmt_xdate()

    logging.info("Finished, saving")
    plt.savefig(args.output)
    plt.show()


if __name__ == "__main__":
    main()
