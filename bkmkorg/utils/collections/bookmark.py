from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

#https://docs.python.org/3/library/dataclasses.html
from dataclasses import dataclass, field, InitVar
import regex
import logging as root_logger
logging = root_logger.getLogger(__name__)

TAG_NORM = regex.compile(" +")
file     = Any

@dataclass
class Bookmark:
    url     : str      = field()
    tags    : Set[str] = field(default_factory=set)
    name    : str      = field(default="No Name")
    tag_sep : str      = field(default=":")
    url_sep : str      = field(default=" : ")

    def __post_init__(self):
        self.tags = [TAG_NORM.sub("_", x.strip()) for x in self.tags]

    def __lt__(self, other):
        return self.url < other.url

    def to_string(self):
        tags = self.url_sep.join(sorted(self.tags))
        return f"{self.url}{self.url_sep}{tags}"

    @staticmethod
    def build(line, url_sep=None, tag_sep=None):
        assert(isinstance(line, str))
        if url_sep is None:
            url_sep = Bookmark.url_sep
        if tag_sep is None:
            tag_sep = Bookmark.tag_sep

        try:
            line_split = line.split(" :")
            url        = line_split[0]
            tags       = line_split[1:]
            tag_set    = set([x.strip() for x in tags])
            if not bool(tag_set):
                logging.warning(f"No Tags for: {url}")

            return Bookmark(url,
                            tag_set,
                            tag_sep=tag_sep,
                            url_sep=url_sep)

        except ValueError as err:
            logging.warning(err)
            logging.warning(line)



@dataclass
class BookmarkCollection:
    entries : List[Bookmark] = field(default_factory=list)
    ext     : str            = field(default=".bookmarks")

    @staticmethod
    def read(f:file) -> "BookmarkCollection":
        bookmarks = BookmarkCollection()
        for line in f.readlines():
            bookmarks += Bookmark.build(line)

        return bookmarks

    def __iadd__(self, value):
        assert(isinstance(value, (BookmarkCollection, Bookmark)))
        if isinstance(value, Bookmark):
            self.entries.append(value)
        elif isinstance(value, BookmarkCollection):
            self.entries += value.entries
