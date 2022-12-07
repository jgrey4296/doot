#/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref
import regex as re

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

def dfs(*dirs:str|pl.Path, ext:None|str|set[str]=None):
    """ DFS a directory for a filetype """
    logging.info("DFSing %s", dirs)
    ext = ext or ".org"
    ext = set([ext]) if not isinstance(ext, set) else ext

    found = []
    queue = [pl.Path(x).expanduser().resolve() for x in dirs]

    while bool(queue):
        current = queue.pop(0)
        assert(current.exists())
        # Add files
        if current.is_file() and current.suffix in ext:
            found.append(current)
        elif current.is_dir():
            queue += [x for x in current.iterdir() if x != ".git"]

    return found
