#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
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
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload, NamedTuple,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from pydantic import BaseModel, field_validator, model_validator

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot._abstract.protocols import Buildable_p, Location_p, ProtocolModelMeta
from doot._structs.dkey import DKey
from doot.utils.dkey_formatter import DKeyFormatter
from doot.mixins.path_manip import PathManip_m
from doot.enums import LocationMeta_f

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

NON_META_KEYS : Final[list[str]] = ["key", "path"]
ARTIFACT_K    : Final[str]       = "__Artifact__"
GLOB          : Final[str]       = "*"
REC_GLOB      : Final[str]       = "**"
SOLO          : Final[str]       = "?"


class Location(BaseModel, Location_p, Buildable_p, PathManip_m, metaclass=ProtocolModelMeta, arbitrary_types_allowed=True):
    """ A Location to be used by tasks in Doot.
      ie: a path, with metadata.

    In toml, can be declared in [[locations]] blocks:
      key = {file='{}'}
      key = {file='{}', protected=true}
    And thus registered in the location store.

    Or in a task's action groups like depends_on, required_for,
      while will be incorporated into a RelationSpec,
      with an anonymous key.
    """
    key                 : None|DKey
    path                : pl.Path
    meta                : LocationMeta_f  = LocationMeta_f.default
    _expansion_keys     : set[str]      = set()

    _toml_str_prefix    : ClassVar[str] = doot.constants.patterns.FILE_DEP_PREFIX
    _artifact_key       : ClassVar[str] = ARTIFACT_K

    class Abstractions(NamedTuple):
        path   : bool = False
        stem   : bool = False
        suffix : bool = False

        def __bool__(self):
            return any((self.path, self.stem, self.suffix))

        def __eq__(self, other:bool|Tuple|Abstractions):
            match other:
                case bool():
                    return other == bool(self)
                case [x,y,z]:
                    return all([self.path==x, self.stem==y, self.suffix==z])
                case Abstractions():
                    return all([self.path==other.path, self.stem==other.stem, self.suffix==other.suffix])

    @classmethod
    def build(cls, data:dict|str, *, key:None|str|DKey=None, target:pl.Path=None):
        match data:
            case Location():
                return cls(key=key or data.key, path=(target or data.path), meta=data.meta)
            case str() | pl.Path():
                assert(target is None)
                return cls(key=key or cls._artifact_key, path=pl.Path(data))
            case dict():
                key = key or data.get("key")
                target = target or data
                return cls(key=key, path=target, meta=data)
            case _:
                raise ValueError("Bad data for Location", data, key, target)

    @field_validator("key", mode="before")
    def _validate_key(cls, val):
        match val:
            case None:
                return DKey(ARTIFACT_K)
            case str():
                return DKey(val, implicit=True)
            case DKey():
                return val

    @field_validator("path", mode="before")
    def _validate_path(cls, val):
        match val:
            case {"path":str()|pl.Path() as val}:
                return pl.Path(val)
            case pl.Path():
                return val
            case str():
                return pl.Path(val)
            case _:
                raise TypeError("Bad path type for location", val)


    @field_validator("meta", mode="before")
    def _validate_metadata(cls, val):
        match val:
            case None:
                return LocationMeta_f.default
            case dict():
                safe_data = {x:y for x,y in val.items() if x not in NON_META_KEYS}
                if not bool(safe_data):
                    return LocationMeta_f.default
                return LocationMeta_f.build(safe_data)
            case LocationMeta_f():
                return val
            case _:
                raise TypeError("Bad type for location metadata", val)

    @model_validator(mode="after")
    def _validate_location(self):
        t_str = str(self.path)
        if self._toml_str_prefix in t_str:
            self.meta |= LocationMeta_f.file
            t_str = t_str.removeprefix(self._toml_str_prefix)
            self.path = pl.Path(t_str)

        if SOLO in t_str:
            self.meta |= LocationMeta_f.abstract
        if GLOB in t_str:
            self.meta |= LocationMeta_f.abstract | LocationMeta_f.glob
        if (keys:=DKeyFormatter.Parse(t_str)[1]):
            self.meta |= LocationMeta_f.abstract | LocationMeta_f.expandable
            self._expansion_keys.update([x.key for x in keys])

        if LocationMeta_f.normOnLoad in self.meta:
            self.path = self._normalize(self.path, root=pl.Path.cwd())

        return self

    def __contains__(self, other:LocationMeta_f|Location|pl.Path) -> bool:
        """ whether a definite artifact is matched by self, an abstract artifact
          a/b/c.py ∈ a/b/*.py
          ________ ∈ a/*/c.py
          ________ ∈ a/b/c.*
          ________ ∈ a/*/c.*
          ________ ∈ **/c.py

        """
        match other:
            case LocationMeta_f():
                return self.check(other)
            case Location():
                path = other.path
            case pl.Path():
                path = other
            case _:
                return False

        if not self.check(LocationMeta_f.abstract):
            return False

        for x,y in zip(self.path.parent.parts, path.parent.parts):
            if x == REC_GLOB or y == REC_GLOB:
                break
            if x == GLOB or y == GLOB:
                continue
            if x != y:
                return False

        _, abs_stem, abs_suff = self.abstracts
        suffix      = abs_suff or self.path.suffix == path.suffix
        stem        = abs_stem or self.path.stem == path.stem
        return  suffix and stem

    def __call__(self) -> pl.Path:
        return self.expand()

    def is_concrete(self) -> bool:
        return LocationMeta_f.abstract not in self.meta

    @ftz.cached_property
    def abstracts(self) -> Location.Abstractions:
        """ Return three bools,
          for is abstract [parent, stem, suffix]
        """
        if self.is_concrete():
            return Location.Abstractions()

        path, stem, suff      = str(self.path.parent), self.path.stem, self.path.suffix
        _path   = bool(GLOB in path or SOLO in path or bool(DKeyFormatter.Parse(path)[1]))
        _stem   = bool(GLOB in stem or SOLO in stem or bool(DKeyFormatter.Parse(stem)[1]))
        _suffix = bool(GLOB in suff or SOLO in suff or bool(DKeyFormatter.Parse(suff)[1]))

        return Location.Abstractions(path=_path, stem=_stem, suffix=_suffix)

    def check(self, meta:LocationMeta_f) -> bool:
        """ return True if this location has any of the test flags """
        return bool(self.meta & meta)

    def exists(self) -> bool:
        expanded = self.expand()
        logging.debug("Testing for existence: %s", expanded)
        return expanded.exists()

    def keys(self) -> set[str]:
        return self._expansion_keys

    def expand(self):
        return doot.locs[self.path]
