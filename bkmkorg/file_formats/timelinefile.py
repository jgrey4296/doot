#!/usr/bin/env python3
##-- imports
from __future__ import annotations

import pathlib as pl
from dataclasses import InitVar, dataclass, field
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)

##-- end imports

@dataclass
class TimelineFile:
    """ TODO File For creating timelines of [Year, Citation] """

    entries : list[Tuple[int, str]] = field(default_factory=list)

    @staticmethod
    def read(f_name:pl.Path):
        pass

    def __iter__(self):
        pass

    def __str__(self):
        pass

    def __iadd__(self, values):
        pass

    def __len__(self):
        pass

    def __contains__(self, value):
        pass

    def add(self, year:int, citation:str):
        pass

class TimelinePlus(TimelineFile):
    """
    TODO timelineplus
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
    pass
