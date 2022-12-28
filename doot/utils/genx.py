#!/usr/bin/env python3
"""
Doot cli xml utils using xmlstarlet
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

if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging


def create_xml(fpath):
    return f"echo '<?xml version=\"1.0\"?><data></data>' | xml fo -R > {fpath}"

def insert_xml(xpath, name, val=None):
    val_str = "-v {val}" if val is not None else ""
    return f"-i {xpath} -t elem -n {elem} {val_str}"

def sub_xml(xpath, name, val=None):
    val_str = "-v '{val}'" if val is not None else ""
    return f"-s {xpath} -t elem -n {name} {val_str}"

def attr_xml(xpath, name, val):
    return f"-i {xpath} -t attr -n {name} -v '{val}'"

def val_xml(xpath, val):
    return f"-s {xpath} -t text -n null -v '{val}'"

def record_xml(xpath, name, val):
    return " ".join([sub_xml(xpath, name),
                     val_xml(f"{xpath}/{name}", val)])
