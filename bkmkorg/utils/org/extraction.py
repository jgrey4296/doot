#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import pathlib as pl
import logging as root_logger
import re
from datetime import Datetime
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
##-- end imports

logging = root_logger.getLogger(__name__)

def get_tweet_dates_and_ids(org_files:list[pl.Path], line_regex=None) -> List[Tuple[Datetime, str]]:
    """
    Extract Tweet id strings and date strings from property drawers in org files
    """
    if line_regex is None:
        line_regex = r"^\s+:PERMALINK:\s+\[.+\[(.+?)\]\]\n\s+:TIME:\s+(.+?)$"

    EXTRACTOR = re.compile(line_regex, flags=re.MULTILINE)
    tweets = []

    for org in org_files:
        logging.debug("Opening %s", org)
        # open org
        with open(org, 'r') as f:
            lines = "\n".join(f.readlines())

        # get all permalink+time pair lines
        found_tweets = EXTRACTOR.findall(lines)
        logging.debug("Found %s", len(found_tweets))
        tweets += found_tweets

    return tweets
