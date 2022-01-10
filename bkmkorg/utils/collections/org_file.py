#!/usr/bin/env python3
"""
TODO refactoring of bkmkorg.io.twitter.file_format_utils into org class
"""
from dataclasses import dataclass, field, InitVar
from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

file = Any

@dataclass
class OrgFile:
 """
 Utility class to create org file format documents
 """

    @staticmethod
    def read(f:file) -> 'OrgFile':
        obj = OrgFile()
        for line in f.readlines():
            pass

        return obj

    def __str__(self):
        """ Output in org plaintext """
        pass

    def __repr__(self):
        """ Summary of org """
        pass
