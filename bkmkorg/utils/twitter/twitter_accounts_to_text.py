#!/usr/bin/env python3
import argparse
import datetime
import json
import logging as root_logger
import re
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import requests

LOGLEVEL = root_logger.DEBUG
LOG_FILE_NAME = "log.{}".format(splitext(split(__file__)[1])[0])
root_logger.basicConfig(filename=LOG_FILE_NAME, level=LOGLEVEL, filemode='w')

console = root_logger.StreamHandler()
console.setLevel(root_logger.INFO)
root_logger.getLogger('').addHandler(console)
logging = root_logger.getLogger(__name__)
##############################

input_date_format = "%a %b %d %H:%M:%S %z %Y"
output_date_format = "%Y:%m"
fields = ["screen_name",
          "followers_count",
          "statuses_count",
          "created_at",
          "name",
          "description",
          "url",
          "status"]

def process_date(the_str):
    the_date = datetime.datetime.strptime(the_str, input_date_format)
    return the_date.strftime(output_date_format)

def full_url(url):
    try:
        return requests.head(url).headers['location']
    except:
        return url


def clean_unicode(the_str):
    if isinstance(the_str, dict):
        return the_str

    clean = str(the_str).encode('ascii', 'ignore').decode()
    return clean.replace('\n', ' ').strip()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog = "\n".join([""]))
    parser.add_argument('--target')
    parser.add_argument('--output')

    args = parser.parse_args()
    args.target = abspath(expanduser(args.target))
    args.output = abspath(expanduser(args.output))

    logging.info(f'Loading {args.target}')
    with open(args.target, 'r') as f:
        data = json.load(f)

    assert(data is not None)

    logging.info(f'Loaded {len(data)}')
    lines = []
    for entry in data:
        # reformat each entry
        # screen_name, followers_count, statuses_count, create_at(year), name, description, url, status date
        try:
            raw = [clean_unicode(entry[x]) if x in entry else f'No {x}' for x in fields]
        except KeyError as err:
            breakpoint()
            logging.info("Failure")

        processed = raw[:3]
        processed += [process_date(raw[3])]
        processed += raw[4:-2]
        if 'http' in raw[-2]:
            processed += [full_url(raw[-2])]
        else:
            logging.info(f'--- Bad url: {raw[-2]}')
            processed += [raw[-2]]
        if 'created_at' in raw[-1]:
            processed += [process_date(raw[-1]['created_at'])]

        assert(not any(["_!_" in x for x in processed])), breakpoint()

        formatted_line = " _!_ ".join([x for x in processed])
        logging.info(f'Adding: {formatted_line}')
        lines.append(formatted_line)


    assert(bool(lines))
    with open(args.output, 'w') as f:
        f.write("\n".join(lines))
