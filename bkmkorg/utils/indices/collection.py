#!/usr/bin/env python3
"""
A Utility class for working with index files,
which map tags to sets of files
"""
##-- imports
from __future__ import annotations

import logging as root_logger
from collections import defaultdict
from dataclasses import InitVar, dataclass, field
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

from bkmkorg.utils.dfs.files import get_data_files
##-- end imports

logging   = root_logger.getLogger(__name__)
IndexFile = "IndexFile"

@dataclass
class IndexFile:
    """ Utility class for `bkmkorg`-wide index file specification and writing """

    mapping : Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(lambda: set()))
    sep     : str                 = field(default=" : ")
    ext     : str                 = field(default=".index")

    @staticmethod
    def builder(target, sep=None) -> IndexFile:
        """
        Build an index file from a target directory or file
        """
        main = IndexFile()
        for target in get_data_files(target, main.ext):
            try:
                main += IndexFile.read(target, sep=sep)
            except Exception as err:
                logging.warning("IndexFile.builder failure for %s", target)

        return main

    @staticmethod
    def read(p:pl.Path, sep=None) -> IndexFile:
        obj  = IndexFile(sep=sep)
        with open(p, 'r') as f:
            # convert lines to mapping
            for line in f.readlines():
                line_s = [x.strip() for x in line.split(obj.sep)]
                obj.add_files(line_s[0], line_s[2:])

        return obj

    def __iadd__(self, value) -> IndexFile:
        """ Merge a bunch of index files together """
        assert(isinstance(value, IndexFile))
        for key,vals in value.mapping.items():
            self.add_files(key, vals)

        return self

    def add_files(self, key, values):
        self.mapping[key].update([str(x) for x in values])

    def __len__(self):
        return len(self.mapping)

    def __str__(self):
        """
        Export the mapping, 1 key per line, as:
        `key` : `len(values)` : ":".join(`values`)
        """
        key_sort = sorted(list(self.mapping.keys()))
        total = [self.sep.join([k, str(len(self.mapping[k]))] + list(self.mapping[k])) for k in key_sort]
        return "\n".join(total)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {len(self)}>"

