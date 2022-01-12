#!/usr/bin/env python3
from typing import List, Set, Dict, Tuple, Optional, Any
from typing import Callable, Iterator, Union, Match
from typing import Mapping, MutableMapping, Sequence, Iterable
from typing import cast, ClassVar, TypeVar, Generic

import argparse
import logging as root_logger
from os import listdir
# Setup root_logger:
from os.path import (abspath, exists, expanduser, isdir, isfile, join, split,
                     splitext)
from typing import (Any, Callable, ClassVar, Dict, Generic, Iterable, Iterator,
                    List, Mapping, Match, MutableMapping, Optional, Sequence,
                    Set, Tuple, TypeVar, Union, cast)

import logging as root_logger
logging = root_logger.getLogger(__name__)

from bkmkorg.utils.bookmark.collection import Bookmark

def exportBookmarks(data:List[Bookmark], filename:str):
    raise DeprecationWarning("use bkmkorg.utils.bookmark.collection.BookmarkCollection")
