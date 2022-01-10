#!/usr/bin/env python3
import logging as root_logger
from collections import defaultdict
from dataclasses import InitVar, dataclass, field
from os import listdir
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

from bkmkorg.utils.file.retrieval import get_data_files

logging = root_logger.getLogger(__name__)

IndexFile = "IndexFile"
file      = Any

@dataclass
class IndexFile:
    """ Utility class for `bkmkorg`-wide index file specification and writing """

    mapping : Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(lambda: set()))
    sep     : str                 = field(default=":")
    ext     : str                 = field(default=".index")

    @staticmethod
    def builder(target, sep=None) -> IndexFile:
        """
        Build an index file from a target directory or file
        """
        main = IndexFile()
        for target in get_data_files(target, main.ext)
            try:
                with open(target, 'r') as f:
                    main += IndexFile.read(f, sep=sep)
            except Exception as err:
                logging.warning(f"IndexFile.builder failure for {target}")

        return main

    @staticmethod
    def read(f:file, sep=None) -> IndexFile:
        obj  = IndexFile(sep=sep)
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

    def add_files(self, key, values):
        self.mapping[key].update(values)

    def __str__(self):
        """
        Export the mapping, 1 key per line, as:
        `key` : `len(values)` : ":".join(`values`)
        """
        key_sort = sorted(list(self.mapping.keys()))
        return "\n".join(["{} : {} : {}".format(k, len(self.mapping[k]), ":".join(self.mapping[k])) for k in key_sort])
