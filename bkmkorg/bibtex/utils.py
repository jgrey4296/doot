#!/usr/bin/env python3
"""

"""
##-- imports

##-- end imports

##-- default imports
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

##-- end default imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

def names_to_pairs(people, entry) -> list[tuple[str, str]]:
    target = set()
    for person in people:
        parts = [" ".join(person[x]).strip() for x in ["first", "last", "von", "jr"]]
        match parts:
            case [only, "", "", ""] | ["", only, "", ""]:
                logging.warning("Only a single name found in %s : %s", entry['ID'], person)
                target.add((only, ""))
            case [first, last, "", ""]:
                target.add((f"{last},", first))
            case [first, last, von, ""]:
                target.add((f"{von} {last},", first))
            case [first, last, "", jr]:
                target.add((f"{last},", f"{jr}, {first}"))
            case [first, last, von, jr]:
                target.add((f"{von} {last},", f"{jr}, {first}"))
            case _:
                logging.warning("Unexpected item in bagging area: %s", parts)

    return target

def names_to_str(people:list, entry, et_al=3) -> list[str]:
    """
    Convert a list of name parts from bibtex into a string
    """
    target = []
    for person in people:
        parts = [" ".join(person[x]).strip() for x in ["first", "last", "von", "jr"]]
        match parts:
            case [only, "", "", ""] | ["", only, "", ""]:
                logging.warning("Only a single name found in %s : %s", entry['ID'], person)
                target.append(only)
            case [first, last, "", ""]:
                target.append(f"{last}, {first}")
            case [first, last, von, ""]:
                target.append(f"{von} {last}, {first}")
            case [first, last, "", jr]:
                target.append(f"{last}, {jr}, {first}")
            case [first, last, von, jr]:
                target.append(f"{von} {last}, {jr}, {first}")
            case _:
                logging.warning("Unexpected item in bagging area: %s", parts)

    if et_al > 0 and len(target) > et_al:
        return f"{target[0]} et al"
    else:
        return " ".join(target)


def year_parse(entry):
    """
    parse the year into a datetime
    """
    if 'year' not in entry:
        year_temp = "2020"
    else:
        year_temp = entry['year']

    if "/" in year_temp:
        year_temp = year_temp.split("/")[0]

    year = datetime.datetime.strptime(year_temp, "%Y")
    entry['__year'] = year
