#!/usr/bin/env python3
"""


See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

import doot
from doot.structs import DootKey

def id_retriever(spec, state) -> list[dict]:
    """ A Null retriever, retruns to dicts to create subtasks from """
    return []

@DootKey.dec.types("files", "exts")
def cli_retriever(spec, state, files, exts):
    """ A CLI retriever, eg: for pre-commit.
      gets the cli arg list "files", and makes a dict that can be used with
      file processors like what walkers use, filtering by extension
    """
    root = doot.locs["."]
    printer.info("CLI Retrieval Testing: %s", files)
    for x in files:
        fpath = doot.locs[x]
        if fpath.suffix not in exts:
            continue

        lpath = fpath.relative_to(root)
        yield dict(name=fpath.stem,
                   fpath=fpath,
                   fstem=fpath.stem,
                   fname=fpath.name,
                   lpath=lpath,
                   pstem=fpath.parent.stem)
