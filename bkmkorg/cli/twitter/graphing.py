#!/usr/bin/env python
# future: load tweet archive, graph tweets, authors etc

##-- imports
from __future__ import annotations
import argparse
import logging as root_logger
from collections import defaultdict
from datetime import datetime
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import pathlib as pl
import bkmkorg.files.collect
from bkmkorg.twitter import counting

from matplotlib import pyplot as plt

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
                                    epilog = "\n".join(["Create graphs of Bibtex Files"]))
parser.add_argument('--library', action="append", help="The bibtex file collection directory", required=True)
parser.add_argument('--target', default="./twitter_timeline.jpg", help="The output target directory")
##-- end argparse


def main():
    args         = parser.parse_args()
    args.library = [pl.Path(x).expanduser().resolve() for x in args.library]
    args.target  = pl.Path(args.target).expanduser().resolve()

    all_orgs = collect.get_data_files(args.library, ".org")

    logging.info("Found %s org files", len(all_orgs))

    # Process tweets
    all_tweets : List[Tuple[datetime, str]] = get_tweet_dates_and_ids(all_orgs)
    logging.info("Found %s tweets", len(all_tweets))
    # remove duplicates and convert date strings
    tweet_dict = {x[0] : convert_tweet_date(x[1]) for x in all_tweets}

    logging.info("Sorting %s tweets", len(tweet_dict))
    ordered = sorted([(x[1], x[0]) for x in tweet_dict.items()], key=lambda x: x[1])

    id_convertor = {x : i for i,x in enumerate(tweet_dict.keys())}

    # Convert to 24 hour time only
    month_counts = counting.convert_to_month_counts(ordered)
    year_counts  = counting.convert_to_year_counts(ordered)
    day_counts   = counting.convert_to_day_counts(ordered)
    time_counts  = counting.convert_to_time_counts(ordered)

    # chart the tweets
    to_draw = [("Month", month_counts),
               ("Year", year_counts),
               ("Day", day_counts),
               ("Time", time_counts)]

    n_rows = int(len(to_draw) / 2)
    n_cols = int(len(to_draw) / 2)
    for count, paired in enumerate(to_draw):
        name, data = paired
        logging.info("Drawing %s", name)
        x = [x[0] for x in data]
        y = [x[1] for x in data]
        plt.subplot(n_rows, n_cols, count + 1)
        plt.plot(x, y, alpha=0.3)
        plt.title(name)
        plt.gcf().autofmt_xdate()

    logging.info("Finished, saving")
    plt.savefig(str(args.target))
    plt.show()


##-- ifmain
if __name__ == "__main__":
    main()

##-- end ifmain
