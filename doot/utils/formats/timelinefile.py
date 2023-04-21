#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import pathlib as pl
from dataclasses import InitVar, dataclass, field
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)

##-- end imports

from datetime import datetime, timedelta
from collections import defaultdict

@dataclass
class TimelineEntry:

    when     : datetime       = field()
    what     : str            = field()
    where    : str            = field()
    duration : None|timedelta = field(default=None)
    tags     : set[str]       = field(default=set)
    urls     : set[str]       = field(default=set)
    who      : set[str]       = field(default=set)

    def __str__(self):
        return ""

    def range(self) -> tuple[datetime, datetime]:
        if self.duration is None:
            return (self.when , self.when)
        return (self.when, self.when + self.duration)


class TimelineFile:
    """
    # Timeline Format:
    # Ext: .timeline

    # For file global tags:
    :tags ....

    # Form One: Event
    year       event country person* :desc .... :tags ... :wiki ....

    # Form Two: Period:
    year -> year event country person_surname* :tags ... :wiki .... :desc ....

    1922 -> 1933 "event"      england blah_bloo bloo_blee :tags blah,blee,blah :link blah
    2003         "something"  usa     a_person            :tags politics       :link https://blah :desc
    """

    date_dict : dict[datetime, list[TimelineEntry]]


    entries : dict[str, TimelineEntry]

    def __init__(self):
        self.date_dict = defaultdict(list)
        self.entries   = dict()
        self.min = None
        self.max = None

    @staticmethod
    def read(fpath:pl.Path):
        result = TimelineFile()
        for line in fpath.read_text().split("\n"):
            # parse line
            data = TimelineEntry()
            results.add(data)

    def __iter__(self):
        for key in sorted(self.date_dict.keys()):
            yield self.date_dict[key]

    def __str__(self):
        results = []
        for entry_group in self:
            results += map(str, entry_group)

        return "\n".join(results)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {len(self)}>"

    def __contains__(self, value):
        match value:
            case datetime():
                return value in self.date_dict
            case TimelineEntry():
                return value.when in self.date_dict

    def __iadd__(self, values):
        match values:
            case [] | None:
                pass
            case [*args]:
                for arg in args:
                    assert(isinstance(arg, TimelineEntry))
                    self.add(arg)
            case TimelineEntry():
                self.add(values)
            case TimelineFile():
                for entrygroup in values:
                    self.add(*entrygroup)

        return self

    def __len__(self):
        return len(self.date_dict)

    def range(self):
        return (self.min, self.max)

    def encompasses(self, value):
        match value:
            case datetime():
                return self.min <= value <= self.max
            case TimelineEntry():
                valMin, valMax = value.range()
                return self.min <= valMin and valMax <= self.max
            case TimelineFile():
                return self.min <= value.min and value.max <= self.max

    def intersects(self, value):
        match value:
            case datetime():
                return self.encompasses(value)
            case TimelineEntry():
                valMin, valMax = value.range()
                return self.min <= valMin or valMax <= self.max
            case TimelineFile():
                left_intersect = self.min <= value.min and self.max <= value.max
                right_intersect = value.min <= self.min and value.max <= self.max
                return left_intersect or right_intersect



    def add(self, *data):
        for entry in data:
            assert(isinstance(entry, TimelineEntry))
            self.date_dict[entry.when].append(entry)
            match self.min, self.max:
                case None, None:
                    self.min = entry.when
                    self.max = entry.when
                case minDate, _ if entry.when < minDate:
                    self.min = entry.when
                case _, maxDate if maxDate < entry.when:
                    self.max = entry.when
