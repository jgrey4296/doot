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
from doot._structs.artifact import DootTaskArtifact
from doot._structs.key import DootKey, DootSimpleKey, DootMultiKey, DootNonKey
from doot.constants import KEY_PATTERN, MAX_KEY_EXPANSIONS

KEY_PAT        = KEY_PATTERN
MAX_EXPANSIONS = MAX_KEY_EXPANSIONS

class DootLocations:
    """
      A Single point of truth for locations that tasks use.
      key=value pairs in [[locations]] toml blocks are integrated into it.
      Also handles key={protect=value} to designate a path shouldn't have files written in it
      by certain io actions

      it expands relative paths according to cwd(),
      but can be used as a context manager to expand from a temp different root

      location designations are of the form:
      key = "location/subdirectory/file"

        If a location value has "loc/{key}/somewhere",
        then for key = "blah", it will be expanded upon access to "loc/blah/somewhere"
    """

    def __init__(self, root:Pl.Path):
        self._root    : pl.Path()       = root.expanduser().absolute()
        self._data    : TomlGuard       = tomlguard.TomlGuard()
        self._protect : set             = set()

    def __repr__(self):
        keys = ", ".join(iter(self))
        return f"<DootLocations : {str(self.root)} : ({keys})>"

    def __getattr__(self, key) -> pl.Path:
        """
          get a location by name from loaded toml
          eg: locs.temp
          """
        if key == "__self__":
            return None
        return self[DootKey.make(key, strict=True)]

    def __getitem__(self, val:str|DootKey|pl.Path|DootTaskArtifact) -> pl.Path:
        """
          eg: doot.locs["{data}/somewhere"]
          A public utility method to easily convert paths.

          Get a location using item access for extending a stored path.
          eg: locs["{temp}/imgs/blah.jpg"]
        """
        match DootKey.make(val, explicit=True):
            case DootNonKey() as key:
                return key.to_path(locs=self)
            case DootSimpleKey() as key:
                return key.to_path(locs=self)
            case DootMultiKey() as key:
                return key.to_path(locs=self)
            case _:
                raise DootLocationExpansionError("Unrecognized location expansion argument", val)

    def __contains__(self, key:str|DootKey|pl.Path|DootTaskArtifact):
        """ Test whether a key is a registered location """
        return key in self._data

    def __iter__(self):
        """ Iterate over the registered location names """
        return iter(self._data.keys())

    def __call__(self, new_root) -> Self:
        """ Create a copied locations object, with a different root """
        new_obj = DootLocations(new_root)
        return new_obj.update(self)

    def __enter__(self) -> Any:
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        return False

    def _calc_path(self, base:pl.Path, *, fallback:pl.Path|None=None) -> pl.Path:
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

    def get(self, key:DootSimpleKey|str, on_fail:None|str|pl.Path=Any) -> None|pl.Path:
        """
          convert a *simple* key of one value to a path.
          This pairs with DootKey.to_path, which does the heavy lifting of expansions
          does *not* expand returned paths
        """
        assert(isinstance(key,(DootSimpleKey,str))), (str(key), type(key))
        match key:
            case DootNonKey():
                return pl.Path(key.form)
            case str() | DootSimpleKey() if key in self._data:
                return pl.Path(self._data[key])
            case _ if on_fail is None:
                return None
            case _ if on_fail != Any:
                return self.get(on_fail)
            case DootSimpleKey():
                return pl.Path(key.form)
            case _:
                return pl.Path(key)

    def expand(self, path:pl.Path, symlinks:bool=False) -> pl.Path:
        return self.normalize(path, symlinks)

    def normalize(self, path:pl.Path, symlinks:bool=False) -> pl.Path:
        """
          Expand a path to be absolute, taking into account the set doot root.
          resolves symlinks unless symlinks=True
        """
        result = path
        match result.parts:
            case ["~", *xs]:
                result = result.expanduser().resolve()
            case ["/", *xs]:
                result = result
            case _:
                result = (self.root / path).expanduser().resolve()

        return result

    @property
    def root(self):
        """
          the registered root location
        """
        return self._root

    def update(self, extra:dict|TomlGuard|DootLocations, strict=True) -> Self:
        """
          Update the registered locations with a dict, tomlguard, or other dootlocations obj.
          The update process itself is tomlguard.tomlguard.merge
        """
        if isinstance(extra, DootLocations):
            return self.update(extra._data)

        assert(isinstance(extra, (tomlguard.TomlGuard,dict)))
        raw          = dict(self._data.items())
        base_keys    = set(raw.keys())
        for k,v in extra.items():
            match v:
                case _ if k in raw and strict:
                    raise DootLocationError("Duplicated Key", k)
                case str():
                    raw[k] = v
                case {"protect": x}:
                    self._protect.add(k)
                    raw[k] = x

        new_keys = set(raw.keys()) - base_keys
        logging.debug("Registered New Locations: %s", ", ".join(new_keys))
        self._data = tomlguard.TomlGuard(raw)

        return self

    def ensure(self, *values, task="doot"):
        """ Ensure the values passed in are registered locations,
          error with DootDirAbsent if they aren't
        """
        missing = set(x for x in values if x not in self)

        if bool(missing):
            raise DootDirAbsent("Ensured Locations are missing for %s : %s", task, missing)


    def check_writable(self, path:pl.Path) -> bool:
        for key in self._protect:
            base = getattr(self, key)
            if path.is_relative_to(base):
                return False

        return True
