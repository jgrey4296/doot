#!~/anaconda/envs/bookmark/bin/python
# future: load tweet archive, graph tweets, authors etc
import argparse
import logging as root_logger
from collections import defaultdict
from datetime import datetime
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

from matplotlib import pyplot as plt

from bkmkorg.utils import diagram as DU
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

def convert_tweet_date(datestring, fmt=None):
    if fmt is None:
        fmt = "%I:%M %p - %d %b %Y"
    if datestring == "None":
        result = datetime.now()
    else:
        result = datetime.strptime(datestring.strip(), fmt)

    return result

def convert_to_time_counts(tweets: List[Tuple[datetime, str]]):
    clock = {x : 0 for x in range(24)}
    for tweet in tweets:
        time = tweet[0].time()
        clock[time.hour] += 1

    return sorted([(x[0], x[1]) for x in clock.items()], key=lambda x: x[0])

def convert_to_year_counts(tweets):
    years = {x : 0 for x in range(2008, 2022)}
    for tweet in tweets:
        year = tweet[0].year
        years[year] += 1

    return sorted([(x[0], x[1]) for x in years.items()], key=lambda x: x[0])


def convert_to_month_counts(tweets):
    months = {x : 0 for x in range(12)}
    for tweet in tweets:
        month = tweet[0].month - 1
        months[month] += 1

    return sorted([(x[0], x[1]) for x in months.items()], key=lambda x: x[0])

def convert_to_day_counts(tweets):
    days = {x : 0 for x in range(31)}
    for tweet in tweets:
        day = tweet[0].day - 1
        days[day] += 1

    return sorted([(x[0], x[1]) for x in days.items()], key=lambda x: x[0])



if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join(["Create graphs of Bibtex Files"]))
    parser.add_argument('--library', action="append", help="The bibtex file collection directory")
    parser.add_argument('--target', default="./twitter_timeline.jpg", help="The output target directory")

    args = parser.parse_args()
    args.library = [abspath(expanduser(x)) for x in args.library]
    args.target = abspath(expanduser(args.target))

    all_orgs = retrieval.get_data_files(args.library, ".org")

    logging.info("Found {} org files".format(len(all_orgs)))

    # Process tweets
    tweets : List[Tuple[datetime, str]] = retrieval.get_tweet_dates_and_ids(all_orgs)
    logging.info("Found {} tweets".format(len(tweets)))
    # remove duplicates and convert date strings
    tweet_dict = {x[0] : convert_tweet_date(x[1]) for x in tweets}

    logging.info("Sorting {} tweets".format(len(tweet_dict)))
    ordered = sorted([(x[1], x[0]) for x in tweet_dict.items()], key=lambda x: x[1])

    id_convertor = {x : i for i,x in enumerate(tweet_dict.keys())}

    # Convert to 24 hour time only
    month_counts = convert_to_month_counts(ordered)
    year_counts  = convert_to_year_counts(ordered)
    day_counts   = convert_to_day_counts(ordered)
    time_counts  = convert_to_time_counts(ordered)

    # chart the tweets
    to_draw = [("Month", month_counts),
                                    ("Year", year_counts),
                                    ("Day", day_counts),
                                    ("Time", time_counts)]
    n_rows = int(len(to_draw) / 2)
    n_cols = int(len(to_draw) / 2)
    for count, paired in enumerate(to_draw):
        name, data = paired
        logging.info("Drawing {}".format(name))
        x = [x[0] for x in data]
        y = [x[1] for x in data]
        plt.subplot(n_rows, n_cols, count + 1)
        plt.plot(x, y, alpha=0.3)
        plt.title(name)
        plt.gcf().autofmt_xdate()

    logging.info("Finished, saving")
    plt.savefig(args.target)
    plt.show()
