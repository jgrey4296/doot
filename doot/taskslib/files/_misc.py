#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


def file_to_hash(filename:pl.Path):
    with open(filename, 'rb') as f:
        return sha256(f.read()).hexdigest()

def map_files_to_hash(files:list[pl.Path]) -> dict[str, int]:
    hash_dict = {}

    for fl in files:
        rel      = fl.relative_to(fl.parent.parent.parent)
        hash_val = file_to_hash(fl)

        hash_dict[str(rel)] = str(hash_val)

    return hash_dict



def hash_all(files:list[pl.Path]) -> tuple[dict, list]:
    """
    Map hashes to files,
    plus hashes with more than one image
    """
    assert(isinstance(files, list))
    assert(all([isinstance(x, pl.Path) for x in files]))
    assert(all([x.is_file() for x in files]))

    hash_dict = {}
    conflicts = {}
    update_num = int(len(files) / 100)
    count = 0
    for i,x in enumerate(files):
        if i % update_num == 0:
            logging.info("%s / 100", count)
            count += 1
        the_hash = file_to_hash(x)
        if the_hash not in hash_dict:
            hash_dict[the_hash] = []
        hash_dict[the_hash].append(x)
        if len(hash_dict[the_hash]) > 1:
            conflicts[the_hash] = len(hash_dict[the_hash])

    return (hash_dict, conflicts)

def find_missing(library:list[pl.Path], others:list[pl.Path]):
    # TODO: handle library hashes that already have a conflict
    library_hash, conflicts = hash_all(library)
    missing = []
    update_num = int(len(others) / 100)
    count = 0
    for i,x in enumerate(others):
        if i % update_num == 0:
            logging.info("%s / 100", count)
            count += 1
        the_hash = file_to_hash(x)
        if the_hash not in library_hash:
            missing.append(x)
    return missing
