#!/usr/bin/env python3
from dataclasses import dataclass, field, InitVar

from bkmkorg.utils.collections.base_format import BaseFileFormat

@dataclass
class TimelineFile(BaseFileFormat):
    """ File For creating timelines of [Year, Citation] """

    entries : List[Tuple[int, str]] = field(default_factory=list)

    @staticmethod
    def read(f:file) -> 'BaseFileFormat':
        pass

    def __iter__(self):
        pass

    def __str__(self):
        pass

    def __iadd__(self, values) -> 'BaseFileFormat':
        pass

    def __len__(self):
        pass

    def __contains__(self, value):
        pass

    def add(self, year:int, citation:str):
        pass

class TimelinePlus(TimelineFile):
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
    pass
