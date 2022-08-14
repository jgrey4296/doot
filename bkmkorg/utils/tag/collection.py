#!/usr/bin/env python3
"""
Utility class for working with tag files
"""
##-- imports
from __future__ import annotations

import pathlib as pl
import logging as root_logger
import re
from collections import defaultdict
from dataclasses import InitVar, dataclass, field
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

from bkmkorg.utils.collections.base_format import BaseFileFormat
from bkmkorg.utils.dfs.files import get_data_files
##-- end imports

logging = root_logger.getLogger(__name__)

TAG_NORM = re.compile(" +")

@dataclass
class TagFile(BaseFileFormat):
    """ A Basic TagFile holds the counts for each tag use """

    count   : Dict[str, int] = field(default_factory=lambda: defaultdict(lambda: 0))
    sep     : str            = field(default=" : ")
    ext     : str            = field(default=".tags")

    norm_regex : re.Pattern  = TAG_NORM


    @staticmethod
    def read(f_name:pl.Path) -> 'TagFile':
        obj = TagFile()
        with open(f_name, 'r') as f:
            for line in f.readlines():
                if not bool(line):
                    continue
                try:
                    line_s = [obj.norm_regex.sub("_", x.strip()) for x in line.split(obj.sep)]
                    obj.set_count(line_s[0], int(line_s[1]))
                except Exception as err:
                    logging.warning(f"Failure Tag Reading: {line}, {err}")

        return obj


    @staticmethod
    def read_bib(f:pl.Path) -> 'TagFile':
        raise NotImplementedError()

    @staticmethod
    def read_org(f:pl.Path) -> 'TagFile':
        raise NotImplementedError()

    @staticmethod
    def read_html(f:pl.Path) -> 'TagFile':
        raise NotImplementedError()

    @staticmethod
    def read_bookmarks(f:pl.Path) -> 'TagFile':
        raise NotImplementedError()

    def __iter__(self):
        return iter(self.count)

    def __str__(self):
        """
        Export the counts, 1 entry per line, as:
        `key` : `value`
        """
        key_sort = sorted(list(self.count.keys()))
        total = [self.sep.join([k, str(self.count[k])]) for k in key_sort]
        return "\n".join(total)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {len(self)}>"

    def __iadd__(self, values):
        assert(isinstance(values, TagFile))
        for key, value in values.count.items():
            norm_key = self.norm_regex.sub("_", key.strip())
            self.count[norm_key] += value

        return self

    def __len__(self):
        return len(self.count)

    def __contains__(self, value):
        return value in self.count

    def inc(self, key, clean=True):
        if not bool(key):
            return
        if clean:
            key = self.norm_regex.sub("_", key.strip())

        self.count[key] += 1

    def set_count(self, key:str, value:int):
        if not bool(key):
            return
        norm_key = self.norm_regex.sub("_", key.strip())
        self.count[norm_key] = value

    def update(self, values):
        for tag in values:
            self.inc(tag)

    def to_set(self) -> Set[str]:
        return set(self.count.keys())

    def get_count(self, tag):
        norm_tag = self.norm_regex.sub("_", tag.strip())
        return self.count[norm_tag]

    def difference(self, other: 'TagFile') -> 'TagFile':
        result = TagFile()
        for tag in other:
            if tag not in self:
                result.set_count(tag, other.get_count(tag))

        return result

@dataclass
class SubstitutionFile(TagFile):
    """ SubstitutionFiles add a replacement tag for some tags """

    ext     : str = field(default=".sub")
    mapping : Dict[str, str] = field(default_factory=lambda: defaultdict(lambda: ""))

    @staticmethod
    def read(f_path:pl.Path) -> 'SubstitutionFile':
        obj = SubstitutionFile()
        with open(f_path, 'r') as f:
            for line in f.readlines():
                if not bool(line.strip()):
                    continue
                try:
                    line_s = [obj.norm_regex.sub("_", x.strip()) for x in line.split(obj.sep)]
                    obj.set_count(line_s[0], int(line_s[1]))
                    if len(line_s) > 2 and bool(line_s[2]):
                        obj.set_sub(line_s[0], line_s[2])
                except:
                    logging.warning(f"Failure Sub Reading: {line}")

        return obj

    def __str__(self):
        """
        Export the mapping, 1 entry per line, as:
        `key` : `count` : `substitution`
        """
        key_sort = sorted(list(self.count.keys()))
        total    = [self.sep.join([k, self.count[k]] + self.mapping[k]) for k in key_sort]
        return "\n".join(total)

    def __iadd__(self, value):
        assert(isinstance(value, SubstitutionFile))
        for key in value.count:
            self.count[key] += value.count[key]
            if key in value.mapping and key not in self.mapping:
                self.mapping[key] = value.mapping[key]
            elif key in self.mapping and key in value.mapping:
                raise Exception(f"Substitution Conflict for {key}")

        return self

    def sub(self, value:str):
        """ apply a substitution if it exists """
        if value in self.mapping:
            return self.mapping[value]

        return value

    def has_sub(self, value):
        return value in self.mapping
    def set_sub(self, key, value):
        if not bool(key):
            return
        self.mapping[key] = value
