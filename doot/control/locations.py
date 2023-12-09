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
import tomlguard
from doot.errors import DootDirAbsent, DootLocationExpansionError, DootLocationError
from doot.structs import DootStructuredName, DootTaskArtifact
from doot.constants import KEY_PATTERN, MAX_KEY_EXPANSIONS
from doot.utils.expansion import expand_path_part

KEY_PAT        = KEY_PATTERN
MAX_EXPANSIONS = MAX_KEY_EXPANSIONS

class DootLocations:
    """
    A Single point of truth for locations tasks use.
    entries in [[locations]] toml blocks are integrated into it.

    it expands relative paths according to cwd(),
    but can be used as a context manager to expand from a temp different root

    location designations are of the form:
    key = "location/subdirectory/file"

    If a location value has "loc/{key}/somewhere",
    then for key = "blah", it will be expanded upon access to "loc/blah/somewhere"
    """

    def __init__(self, root:Pl.Path):
        self._root : pl.Path()    = root.expanduser().absolute()
        self._data : TomlGuard       = tomlguard.TomlGuard()


    def __repr__(self):
        keys = ", ".join(iter(self))
        return f"<DootLocations : {str(self.root)} : ({keys})>"

    def __getattr__(self, key) -> pl.Path:
        """
          get a location by name from loaded toml
          eg: locs.temp
        """
        return self.get(key)

    def __getitem__(self, val:str|pl.Path|DootTaskArtifact) -> pl.Path:
        """
          Get a location using item access for extending a stored path.
          eg: locs["{temp}/imgs/blah.jpg"]
        """
        match val:
            case str() | pl.Path():
                return self.get(val)
            case DootTaskArtifact():
                return self.get(val.path)
            case _:
                raise DootLocationExpansionError("Unrecognized location expansion argument", val)

    def __contains__(self, key):
        """ Test whether a key is a registered location """
        return key in self._data

    def __iter__(self):
        """ Iterate over the registered location names """
        return iter(self._data.keys())

    def _calc_path(self, base:path, *, fallback:pl.Path|None=None) -> pl.Path:
        """
          Expands a string or key according to registered locations into a path.
          so if locs = {"base": "~/Desktop", "bloo": "bloo/sub/dir"}
          then:
          _calc_path("base") -> "~/Desktop"
          _calc_path("{base}/blah") -> "~/Desktop/blah"
          _calc_path("{base}/{bloo}") -> "~/Desktop/bloo/sub/dir"
        """
        expansion = pl.Path()

        # Expand each part:
        try:
            for part in base.parts:
                expanded_part = expand_path_part(part.strip(), self._data)
                # build the total expansion from the parts
                logging.debug("Expanded %s -> %s", part, expanded_part)
                expansion /= expanded_part
        except (DootLocationExpansionError, DootLocationError) as err:
            if fallback is not None:
                logging.debug("Expansion failed, using fallback: %s -> %s", base, fallback)
                expansion = pl.Path(fallback)
            else:
                raise err

        logging.debug("Expansion Result: %s", expansion)
        # Force the path to be absolute
        match expansion.parts:
            case []:
                return self.root
            case ["~", *_]:  # absolute path or home
                return expansion.expanduser().absolute()
            case ["/", *_]:
                return expansion.absolute()
            case _:
                return self.root / expansion

    def get(self, key, fallback=None):
        """
          Get an expanded path key, but if it fails, return the fallback value
        """
        assert(isinstance(fallback, None|pl.Path))
        if key in self._data:
            logging.info("Accessing %s -> %s", key, self._data[key])
            return self._calc_path(pl.Path(self._data[key]), fallback=fallback)
        else:
            return self._calc_path(pl.Path(key), fallback=fallback)


    @property
    def root(self):
        """
          the registered root location
        """
        return self._root

    def update(self, extra:dict|TomlGuard|DootLocations):
        """
          Update the registered locations with a dict, tomlguard, or other dootlocations obj.
          The update process itself is tomlguard.tomlguard.merge
        """
        current_keys = set(self._data.keys())
        match extra:
            case dict() | tomlguard.TomlGuard():
                self._data = tomlguard.TomlGuard.merge(self._data, extra)
            case DootLocations():
                self._data = tomlguard.TomlGuard.merge(self._data, extra._data)
            case _:
                raise TypeError("Bad type passed to DootLocations for updating: %s", type(extra))

        new_keys = set(self._data.keys()) - current_keys
        logging.debug("Registered New Locations: %s", ", ".join(new_keys))

        return self

    def ensure(self, *values, task="doot"):
        """ Ensure the values passed in are registered locations,
          error with DootDirAbsent if they aren't
        """
        missing = set(x for x in values if x not in self)

        if bool(missing):
            raise DootDirAbsent("Ensured Locations are missing for %s : %s", task, missing)

    def __call__(self, new_root) -> Self:
        """ Create a copied locations object, with a different root """
        new_obj = DootLocations(new_root)
        return new_obj.update(self)

    def __enter__(self) -> Any:
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        return False
