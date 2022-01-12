#!/usr/bin/env python3
"""
Utility class for working with tag files
"""
from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir
from collections import defaultdict
from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic
from collections import defaultdict
from dataclasses import dataclass, field, InitVar

from bkmkorg.utils.file.retrieval import get_data_files
import logging as root_logger
logging = root_logger.getLogger(__name__)

file = Any

@dataclass
class TagFile:
    """ A Basic TagFile holds the counts for each tag use """

    mapping : Dict[str, str] = field(default_factory=dict)
    count   : Dict[str, int] = field(default_factory=lambda: defaultdict(lambda: 0))
    sep     : str            = field(default=":")
    ext     : str            = field(default=".tags")

    @classmethod
    def builder(cls, target):
        """
        Build an tag file from a target directory or file
        """
        main = cls()
        for t in get_data_files(target, main.ext):
            try:
                with open(t, 'r') as f:
                    main += cls.read(f)
            except Exception as err:
                logging.warning(f"{cls.__name__} creation failure with {t}")

        return main

    @staticmethod
    def read(f:file) -> 'TagFile':
        obj = TagFile()
        for line in f.readlines():
            line_s = [x.strip() for x in line.split(obj.sep)]
            obj.set_count(line_s[0], int(line_s[1]))

        return obj


    @staticmethod
    def read_bib(f:file) -> 'TagFile':
        raise NotImplementedError()

    def read_org(f:file) -> 'TagFile':
        raise NotImplementedError()

    def read_html(f:file) -> 'TagFile':
        raise NotImplementedError()

    def inc(self, key):
        self.mapping[key] += 1

    def set_tag(self, key, value):
        self.mapping[key] = value

    def set_count(self, key, value):
        self.count[key] = value

    def __str__(self):
        """
        Export the mapping, 1 entry per line, as:
        `key` : `value`
        """
        key_sort = sorted(list(self.mapping.keys()))
        return "\n".join(["{} : {}".format(k, self.mapping[k])])

    def __iadd__(self, value):
        assert(isinstance(value, TagFile))
        for key, value in value.mapping:
            self.mapping[key] += value

    def __len__(self):
        return len(self.count)
@dataclass
class SubstitutionFile(TagFile):
    """ SubstitutionFiles add a replacement tag for some tags """

    ext : str = field(default=".sub")

    @staticmethod
    def read(f:file) -> 'SubstitutionFile':
        obj = SubstitutionFile()
        for line in f.readlines():
            line_s = [x.strip() for x in line.split(obj.sep)]
            obj.set_count(line_s[0], line_s[1])
            if len(line_s) > 2 and line_s[2] != "":
                obj.set_sub(line_s[0], line_s[2])

        return obj

    def __str__(self):
        """
        Export the mapping, 1 entry per line, as:
        `key` : `count` : `substitution`
        """
        key_sort = sorted(list(self.count.keys()))
        return "\n".join(["{} : {} : {} ".format(k, self.count[k], self.mapping[k])])

    def __iadd__(self, value):
        assert(isinstance(value, SubstitutionFile))
        for key in value.count:
            self.count[key] += value.count[key]
            if key in value.mapping and key not in self.mapping:
                self.mapping[key] = value.mapping[key]
            elif key in self.mapping and key in value.mapping:
                raise Exception(f"Substitution Conflict for {key}")

    def sub(self, value:str):
        """ apply a substitution if it exists """
        if value in self.mapping:
            return self.mapping[value]

        return value
