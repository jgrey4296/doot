from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

#https://docs.python.org/3/library/dataclasses.html
from dataclasses import dataclass, field, InitVar

import logging as root_logger
logging = root_logger.getLogger(__name__)

@dataclass
class Bookmark:
    url     : str      = field()
    tags    : Set[str] = field(default_factory=set)
    name    : str      = field(default="No Name")
    tag_sep : str      = field(default=":")
    url_sep : str      = field(default=" : ")

    def to_string(self):
        tags = self.url_sep.join(sorted(self.tags))
        return f"{self.url}{self.url_sep}{tags}\n"

    @staticmethod
    def build(line, url_sep=None, tag_sep=None):
        assert(isinstance(line, str))
        if url_sep is None:
            url_sep = Bookmark.url_sep
        if tag_sep is None:
            tag_sep = Bookmark.tag_sep

        try:
            url, tags = line.split(" :")
            tag_set = set([x.strip() for x in tags.strip().split(":")])
            if not bool(tag_set):
                logging.warning(f"No Tags for: {url}")

            return Bookmark(url,
                            tag_set,
                            tag_sep=tag_sep,
                            url_sep=url_sep)

        except ValueError as err:
            logging.warning(err)
            logging.warning(line)
