#!/usr/bin/env python3
"""
Utility class for Twitter Archive Automation,
reads a todo file, ready for downloading, org translation and tagging
"""

##-- imports
from __future__ import annotations

import pathlib as pl
import re
from collections import defaultdict
from dataclasses import InitVar, dataclass, field
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeAlias, TypeVar, Union, cast)

##-- end imports

TagSet : TypeAlias = set[str]
ID     : TypeAlias = str

tag_map : Final[Callable] = lambda: defaultdict(list)

@dataclass
class TweetTodoFile:
    """
    Read a file of tweet references and their tags

    """
    tags_mapping : dict[ID, TagSet] = field(default_factory=tag_map)
    sep          : str              = field(default="_:_")
    ext          : str              = field(default=".tweets")
    remainder    : List[str]        = field(default_factory=list)

    @staticmethod
    def read(p:pl.Path, id_regex=r"status/(\d+)\??"):
        obj   = TweetTodoFile()
        reg   = re.compile(id_regex)
        with open(p, 'r') as f:
            lines = f.readlines()

        for line in lines:
            try:
                url, tags         = line.split(obj.sep)
                id_n              = reg.search(url)[1]
                obj.tags_mapping[id_n].update(tags.strip().split(","))
            except:
                obj.remainder.append(line)

        return obj

    def __len__(self):
        return len(self.tags_mapping)

    def __bool__(self):
        return bool(self.tags_mapping)

    def ids(self) -> Set[ID]:
        return set(self.tags_mapping.keys())
