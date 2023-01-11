"""
Provide Utility classes for working with bookmarks
"""
##-- imports
from __future__ import annotations

import logging as root_logger
import pathlib as pl
import urllib.parse as url_parse
from dataclasses import InitVar, dataclass, field
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import regex
from bkmkorg.collections.base_format import BaseFileFormat
from bs4 import BeautifulSoup
##-- end imports

logging = root_logger.getLogger(__name__)

TAG_NORM = regex.compile(" +")

@dataclass
class Bookmark:
    url     : str      = field()
    tags    : Set[str] = field(default_factory=set)
    name    : str      = field(default="No Name")
    sep     : str      = field(default=" : ")

    def __post_init__(self):
        self.tags = {TAG_NORM.sub("_", x.strip()) for x in self.tags}

    def __eq__(self, other):
        return self.url == other.url

    def __lt__(self, other):
        return self.url < other.url

    def __str__(self):
        tags = self.sep.join(sorted(self.tags))
        return f"{self.url}{self.sep}{tags}"

    @staticmethod
    def build(line, sep=None):
        assert(isinstance(line, str))
        if sep is None:
            sep = Bookmark.sep

        line_split = line.split(sep)
        url        = line_split[0]
        tag_set    = {x.strip() for x in line_split[1:]}
        if not bool(tag_set):
            logging.warning("No Tags for: %s", url)

        return Bookmark(url,
                        tag_set,
                        sep=sep)


    @property
    def url_comps(self) -> url_parse.ParseResult:
        return url_parse.urlparse(self.url)

    def merge(self, other) -> 'Bookmark':
        assert(self == other)
        merged = Bookmark(self.url,
                          self.tags.union(other.tags),
                          self.name,
                          sep=self.sep)
        return merged

    def clean(self, subs):
        cleaned_tags = set()
        for tag in self.tags:
            cleaned_tags.add(subs.sub(tag))

        self.tags = cleaned_tags

@dataclass
class BookmarkCollection(BaseFileFormat):

    entries : List[Bookmark] = field(default_factory=list)
    ext     : str            = field(default=".bookmarks")


    @staticmethod
    def read(f_name:pl.Path) -> "BookmarkCollection":
        """ Read a file to build a bookmark collection """
        bookmarks = BookmarkCollection()
        with open(f_name, 'r') as f:
            for line in f.readlines():
                bookmarks += Bookmark.build(line)

        return bookmarks

    @staticmethod
    def read_netscape(path:pl.Path):
        logging.info('Starting html opener for: %s', path)
        with open(path, 'rb') as f:
            rawHtml = f.read().decode("utf-8","ignore")

        soup     = BeautifulSoup(rawHtml,'html.parser')
        bkmkList = _getLinks(soup)
        logging.info("Found %s links", len(bkmkList))
        return BookmarkCollection(bkmkList)

    def add_file(self, f_name:pl.Path):
        with open(f_name, 'r') as f:
            for line in f.readlines():
                self.entries.append(Bookmark.build(line))

    def __str__(self):
        return "\n".join([str(x) for x in sorted(self.entries)])

    def __repr__(self):
        return f"<{self.__class__.__name__}: {len(self)}>"

    def __iadd__(self, value):
        assert(isinstance(value, (BookmarkCollection, Bookmark, list)))
        if isinstance(value, Bookmark):
            self.entries.append(value)
        elif isinstance(value, BookmarkCollection):
            self.entries += value.entries
        elif isinstance(value, list):
            assert(all([isinstance(x, Bookmark) for x in value]))
            self.entries += value
        else:
            raise TypeError(type(value))

        return self

    def __iter__(self):
        return iter(self.entries)

    def __contains__(self, value:Bookmark):
        return value in self.entries

    def __len__(self):
        return len(self.entries)

    def difference(self, other:"BookmarkCollection"):
        result = BookmarkCollection()
        for bkmk in other:
            if bkmk not in self:
                result += bkmk

        return result

    def merge_duplicates(self):
        deduplicated = {}
        for x in self:
            if x.url not in deduplicated:
                deduplicated[x.url] = x
            else:
                deduplicated[x.url] = x.merge(deduplicated[x.url])

        self.entries = list(deduplicated.values())

##-- utils
def _getLinks(aSoup) -> List[Bookmark]:
    bkmks = aSoup.find_all('a')
    bkmkList = []
    for x in bkmks:
        tagString = x.get('tags')
        if tagString is not None:
            indTags = tagString.split(',')
        else:
            indTags = []
        tagSet = set(indTags)
        newBkmk = Bookmark(x.get('href'),tagSet, name=x.get_text())
        bkmkList.append(newBkmk)

    return bkmkList

##-- end utils
