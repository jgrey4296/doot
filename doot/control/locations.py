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

import os
import re
import tomlguard
import doot
from doot.errors import DootDirAbsent, DootLocationExpansionError, DootLocationError
from doot.structs import DootTaskArtifact, DootKey, TomlLocation
from doot._structs.key import DootSimpleKey, DootMultiKey, DootNonKey
from doot.mixins.path_manip import PathManip_m
from doot.enums import LocationMeta

KEY_PAT        = doot.constants.patterns.KEY_PATTERN
MAX_EXPANSIONS = doot.constants.patterns.MAX_KEY_EXPANSIONS

class DootLocations(PathManip_m):
    """
      A Single point of truth for task access to locations.
      key=value pairs in [[locations]] toml blocks are integrated into it.

      it expands relative paths according to cwd(),
      but can be used as a context manager to expand from a temp different root

      location designations are of the form:
      key = 'location/subdirectory/file'
      simple locations can be accessed as attributes: locs.temp

      more complex locations, with expansions, are accessed as items:
      locs['{temp}/somewhere']
      will expand 'temp' (if it is a registered location)
      """
    locmeta = LocationMeta

    def __init__(self, root:Pl.Path):
        self._root    : pl.Path()               = root.expanduser().absolute()
        self._data    : dict[str, TomlLocation] = dict()
        self._loc_ctx : None|DootLocations      = None

    def __repr__(self):
        keys = ", ".join(iter(self))
        return f"<DootLocations : {str(self.root)} : ({keys})>"

    def __getattr__(self, key) -> pl.Path:
        """
          get a location by name from loaded toml
          delegates to __getitem__
          eg: locs.temp
          """
        if key == "__self__":
            return None
        return self[DootKey.build(key, strict=True)]

    def __getitem__(self, val:str|DootKey|pl.Path|DootTaskArtifact) -> pl.Path:
        """
          eg: doot.locs['{data}/somewhere']
          A public utility method to easily convert paths.
          delegates to DootKey's path expansion

          Get a location using item access for extending a stored path.
          eg: locs['{temp}/imgs/blah.jpg']
        """
        match DootKey.build(val, explicit=True):
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

    def __iter__(self) -> Generator[str]:
        """ Iterate over the registered location names """
        return iter(self._data.keys())

    def __call__(self, new_root=None) -> Self:
        """ Create a copied locations object, with a different root """
        new_obj = DootLocations(new_root or self._root)
        return new_obj.update(self)

    def __enter__(self) -> Any:
        """ replaces the global doot.locs with this locations obj,
        and changes the system root to wherever this locations obj uses as root
        """
        self._loc_ctx = doot.locs
        doot.locs = self
        os.chdir(doot.locs._root)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> bool:
        """ returns the global state to its original, """
        assert(self._loc_ctx is not None)
        doot.locs     = self._loc_ctx
        os.chdir(doot.locs._root)
        self._loc_ctx = None
        return False

    def get(self, key:DootSimpleKey|str, on_fail:None|str|pl.Path=Any) -> None|pl.Path:
        """
          convert a *simple* key of one value to a path.
          does *not* recursively expand returned paths
          More complex expansion is handled in DootKey and subclasses
        """
        assert(isinstance(key,(DootSimpleKey,str))), (str(key), type(key))
        match key:
            case DootNonKey():
                return pl.Path(key.form)
            case str() | DootSimpleKey() if key in self._data:
                return self._data[key].base
            case _ if on_fail is None:
                return None
            case _ if on_fail != Any:
                return self.get(on_fail)
            case DootSimpleKey():
                return pl.Path(key.form)
            case _:
                return pl.Path(key)

    def normalize(self, path:pl.Path, symlinks:bool=False) -> pl.Path:
        """
          Expand a path to be absolute, taking into account the set doot root.
          resolves symlinks unless symlinks=True
        """
        return self._normalize(path, root=self.root)

    def metacheck(self, key:str|DootKey, meta:LocationMeta) -> bool:
        """ check if any key provided has the applicable meta flags """
        match key:
            case DootNonKey():
                return False
            case DootSimpleKey() if key in self._data:
                return self._data[key].check(meta)
            case DootMultiKey():
                 for k in DootKey.build(key):
                     if k not in self._data:
                         continue
                     if self._data[k].check(meta):
                         return True
            case str():
                return self.metacheck(DootKey.build(key), meta)
        return False

    @property
    def root(self):
        """
          the registered root location
        """
        return self._root

    def update(self, extra:dict|TomlGuard|DootLocations, strict=True) -> Self:
        """
          Update the registered locations with a dict, tomlguard, or other dootlocations obj.
        """
        match extra: # unwrap to just a dict
            case dict():
                pass
            case tomlguard.TomlGuard():
                return self.update(extra._table())
            case DootLocations():
                return self.update(extra._data)
            case _:
                raise doot.errors.DootLocationError("Tried to update locations with unknown type: %s", extra)

        raw          = dict(self._data.items())
        base_keys    = set(raw.keys())
        new_keys     = set()
        for k,v in extra.items():
            match TomlLocation.build(k, v):
                case _ if k in new_keys and v != raw[k]:
                    raise DootLocationError("Duplicated, non-matching Key", k)
                case _ if k in base_keys:
                    logging.debug("Skipping Location update of: %s", k)
                    pass
                case TomlLocation() as l if l.check(LocationMeta.normOnLoad):
                    raw[l.key] = TomlLocation.build(k, v, base=self.normalize(l.base))
                    new_keys.add(l.key)
                case TomlLocation() as l:
                    raw[l.key] = l
                    new_keys.add(l.key)
                case _:
                    raise DootLocationError("Couldn't build a TomlLocation for: (%s : %s)", k, v)

        logging.debug("Registered New Locations: %s", ", ".join(new_keys))
        self._data = raw
        return self

    def ensure(self, *values, task="doot"):
        """ Ensure the values passed in are registered locations,
          error with DootDirAbsent if they aren't
        """
        missing = set(x for x in values if x not in self)

        if bool(missing):
            raise DootDirAbsent("Ensured Locations are missing for %s : %s", task, missing)

    def _clear(self):
        self._data = tomlguard.TomlGuard()
