#!/usr/bin/env python3
"""
Utility class for Twitter Archive Automation,
reads a todo file, ready for downloading, org translation and tagging
"""

##-- imports
from __future__ import annotations

import pathlib as pl
from dataclasses import InitVar, dataclass, field
from collections import defaultdict
import re
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)
##-- end imports

Tag  = str
ID   = str

todo_map = lambda: defaultdict(lambda: "")

@dataclass
class TweetTodoFile:
    mapping   : Dict[ID, Tag]  = field(default_factory=todo_map)
    sep       : str            = field(default="_:_")
    ext       : str            = field(default=".tweets")
    remainder : List[str]      = field(default_factory=list)

    @staticmethod
    def read(p:pl.Path, id_regex=r"status/(\d+)\?"):
        obj   = TweetTodoFile()
        reg   = re.compile(id_regex)
        with open(p, 'r') as f:
            lines = f.readlines()

        for line in lines:
            try:
                url, tags         = line.split(obj.sep)
                id_n              = reg.search(url)[1]
                obj.mapping[id_n] += tags.strip() + ","
            except:
                obj.remainder.append(line)

        return obj

    def __len__(self):
        return len(self.mapping)

    def __bool__(self):
        return bool(self.mapping)

    def ids(self) -> Set[ID]:
        return set(self.mapping.keys())
