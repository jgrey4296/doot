"""
Utility to open and parse a netscape bookmark file
https://docs.microsoft.com/en-us/previous-versions/windows/internet-explorer/ie-developer/platform-apis/aa753582(v=vs.85)
"""
from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

import logging
import os
from collections import namedtuple
from bs4 import BeautifulSoup

from bkmkorg.utils.bookmark.collection import Bookmark

def open_and_extract_bookmarks(filename) -> List[Bookmark]:
    """
    The Main Utility. Takes the path to a filename, returns a list of bookmarks
    """
    raise DeprecationWarning("Use bkmkorg.utils.bookmarks.collection.BookmarkCollection")
