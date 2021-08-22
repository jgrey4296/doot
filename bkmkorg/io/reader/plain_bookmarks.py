from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

from os.path import join, isfile, exists, abspath
from os.path import split, isdir, splitext, expanduser
from os import listdir
import re

import logging as root_logger
logging = root_logger.getLogger(__name__)

from bkmkorg.utils.bookmark.bookmark import Bookmark

ext = ".bookmarks"

def load_plain_file(path, ext=ext) -> List[Bookmark]:
    """ Load a plain bookmarks file where each line is:
    url : tag,tag,...

    Expects an expanded path
    Returns: List[]
    """
    logging.info(f"Loading plain bookmarks: {path}")
    assert(exists(path))
    assert(splitext(path)[1] == ext), splitext(path)[1]
    bookmarks = []
    # open file
    lines = []
    with open(path, 'r') as f:
        lines = f.readlines()

    logging.info(f"Found {len(lines)} lines")
    for line in lines:
        bookmarks.append(Bookmark.build(line))

    return bookmarks
