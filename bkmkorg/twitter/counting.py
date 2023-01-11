#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

from bkmkorg.org.extraction import get_tweet_dates_and_ids

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

def convert_tweet_date(datestring, fmt=None):
    if fmt is None:
        fmt = "%I:%M %p - %d %b %Y"
    if datestring == "None":
        result = datetime.now()
    else:
        result = datetime.datetime.strptime(datestring.strip(), fmt)

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
