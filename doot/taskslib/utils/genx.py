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
from importlib.resources import files
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

##-- data
data_path    = files("doot.__templates")
xml_template = data_path.joinpath("xl_template")
##-- end data

def create_xml(fpath):
    fpath.write_text(xml_template.read_text())
    # return f"echo '<?xml version=\"1.0\"?><data></data>' | xml fo -R > {fpath}"

def insert_xml(xpath, name, val=None) -> list:
    """ insert an element before the xpath element """
    val_cmd = ["-v", val] if val is not None else []
    return ["-i", xpath, "-t", "elem", "-n", name] + val_cmd

def sub_xml(xpath, name, val=None) -> list:
    """ insert an element within the xpath element """
    val_cmd = ["-v", val] if val is not None else []
    return ["-s", xpath, "-t", "elem", "-n", name] + val_cmd

def attr_xml(xpath, name, val) -> list:
    """ set the attribute of an xpath element """
    return ["-i", xpath,  "-t", "attr", "-n",  name, "-v",  val]

def val_xml(xpath, val) -> list:
    return ["-s", xpath, "-t", "text", "-n", "null", "-v", val]

def record_xml(xpath, name, val) -> list:
    return sub_xml(xpath, name) + val_xml(f"{xpath}/{name}", val)
