#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field, replace
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
# If CLI:
# logging = logmod.root
# logging.setLevel(logmod.NOTSET)
##-- end logging

import re
import tomler
from doot.errors import DootDirAbsent, DootLocationExpansionError, DootLocationError
from doot.structs import DootStructuredName

KEY_PAT        = re.compile("{(.+?)}")
MAX_EXPANSIONS = 10

class DootLocations:
    """
    A Single point of truth for locations tasks use.
    entries in [[locations]] toml blocks are integrated into it.

    it expands relative paths according to cwd(),
    but can be used as a context manager to expand from a temp different root

    location designations are of the form:
    key = "location/directory"

    If a location value has "loc/{key}/somewhere",
    then for key = "blah", it will be expanded upon access to "loc/blah/somewhere"
    """

    def __init__(self, root:Pl.Path):
        self._root : pl.Path()    = root.expanduser().absolute()
        self._data : Tomler       = tomler.Tomler()


    def __repr__(self):
        keys = ", ".join(iter(self))
        return f"<DootLocations : {str(self._root)} : ({keys})>"

    def __getattr__(self, val) -> pl.Path:
        """
          get a location by name from loaded toml
        """
        try:
            return self._calc_path(val, self._data[val])
        except tomler.TomlAccessError as err:
            raise DootLocationError("Missing Location: %s",  str(err)) from err

    def __getitem__(self, val) -> pl.Path:
        return self.__getattr__(val)

    def __contains__(self, val):
        return val in self._data

    def __iter__(self):
        return iter(self._data.keys())

    def _calc_path(self, key, val) -> pl.Path:
        base      = val
        count     = 0
        while m := re.search(KEY_PAT, base):
            if count > MAX_EXPANSIONS:
                raise DootLocationExpansionError("Root key: %s, original: %s, last expansion: %s", key, val, base)
            count += 1
            wr_key  = m[0]
            sub_val = self._data[m[1]]
            base = re.sub(wr_key, sub_val, base)

        match str(base)[0]:
            case "~":  # absolute path or home
                return pl.Path(base).expanduser().absolute()
            case "/":
                return pl.Path(base).absolute()
            case _:
                return self.root / base

    def get(self, val, default=None):
        try:
            return self.__getattr__(val)
        except tomler.TomlAccessError as err:
            if default is not None:
                return self._calc_path(val, default)
            raise err


    @property
    def root(self):
        return self._root

    def update(self, extra:dict|Tomler|DootLocations):
        match extra:
            case dict() | tomler.Tomler():
                self._data = tomler.Tomler.merge(self._data, extra)
            case DootLocations():
                self._data = tomler.Tomler.merge(self._data, extra._data)
            case _:
                raise TypeError("Bad type passed to DootLocations for updating: %s", type(extra))

        return self

    def ensure(self, *values, task="doot"):
        missing = set(x for x in values if x not in self)

        if bool(missing):
            raise DootDirAbsent("Ensured Locations are missing for %s : %s", task, missing)

    def __call__(self, new_root) -> Self:
        new_obj = DootLocations(new_root)
        return new_obj.update(self)

    def __enter__(self) -> Any:
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        return False
