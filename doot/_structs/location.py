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
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
# import more_itertools as mitz
# from boltons import
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from pydantic import BaseModel, model_validator, field_validator
import doot
from doot.enums import LocationMeta_f
from doot._structs.dkey import DKey
from doot._abstract.protocols import ProtocolModelMeta, Location_p, Buildable_p
from doot.utils.dkey_formatter import DKeyFormatter

GLOB     : Final[str] = "*"
REC_GLOB : Final[str] = "**"
SOLO     : Final[str] = "?"

class Location(BaseModel, Location_p, Buildable_p, metaclass=ProtocolModelMeta, arbitrary_types_allowed=True):
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
    key                 : None|str|DKey
    path                : pl.Path
    meta                : LocationMeta_f  = LocationMeta_f.default
    _expansion_keys     : set[str]      = set()

    _toml_str_prefix    : ClassVar[str] = doot.constants.patterns.FILE_DEP_PREFIX
    _artifact_key           : ClassVar[str] = DKey("!!Artifact!!")

    @classmethod
    def build(cls, data:dict|str, *, key:None|str|DKey=None, target:pl.Path=None):
        match data:
            case Location():
                return cls(key=key or data.key, path=(target or data.path), meta=data.meta)
            case str() if data.startswith(cls._toml_str_prefix):
                # prefixed str: file:>a/simple/path.txt
                assert(target is None)
                the_path = pl.Path(data.removeprefix(cls._toml_str_prefix))
                meta     = LocationMeta_f.file
                return cls(key=key or cls._artifact_key, path=the_path, meta=meta)
            case str() | pl.Path():
                assert(target is None)
                return cls(key=key or cls._artifact_key, path=pl.Path(data))
            case {"loc": target_s}:
                key    = key or data.get("key")
                target = target or pl.Path(target_s.removeprefix(cls._toml_str_prefix))
                meta   = LocationMeta_f.build({x:y for x,y in data.items() if x != "loc"})
                if target_s.startswith(cls._toml_str_prefix):
                    meta |= LocationMeta_f.file
                return cls(key=key, path=target, meta=meta)
            case {"file": target_s}:
                key    = key or data.get("key", key)
                target = target or pl.Path(target_s.removeprefix(cls._toml_str_prefix))
                meta   = LocationMeta_f.build({x:y for x,y in data.items() if x != "loc"})
                meta |= LocationMeta_f.file
                return cls(key=key, path=target, meta=meta)
            case dict() if target is not None:
                key = key or data.get("key", key)
                meta   = LocationMeta_f.build({x:y for x,y in data.items()})
                return cls(key=key, path=target, meta=meta)
            case _:
                raise ValueError("Bad data for Location", data, key, target)

    @model_validator(mode="after")
    def _validate_metadata(self):
        t_str = str(self.path)
        if SOLO in t_str:
            self.meta |= LocationMeta_f.abstract
        if GLOB in t_str:
            self.meta |= LocationMeta_f.abstract | LocationMeta_f.glob
        if (keys:=DKeyFormatter.Parse(t_str)):
            self.meta |= LocationMeta_f.abstract | LocationMeta_f.expandable
            self._expansion_keys.update([x[0] for x in keys])

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

    @ftz.cached_property
    def abstracts(self) -> tuple[bool, bool, bool]:
        """ Return three bools,
          for is abstract [parent, stem, suffix]
        """
        if LocationMeta_f.abstract not in self.meta:
            return (False, False, False)
        path, stem, suff      = str(self.path.parent), self.path.stem, self.path.suffix
        _path   = bool(GLOB in path or SOLO in path or bool(DKeyFormatter.Parse(path)))
        _stem   = bool(GLOB in stem or SOLO in stem or bool(DKeyFormatter.Parse(stem)))
        _suffix = bool(GLOB in suff or SOLO in suff or bool(DKeyFormatter.Parse(suff)))

        return (_path, _stem, _suffix)

    def check(self, meta:LocationMeta_f) -> bool:
        return meta in self.meta

    def exists(self) -> bool:
        expanded = self.expand()
        logging.debug("Testing for existence: %s", expanded)
        return expanded.exists()

    def keys(self) -> set[str]:
        return self._expansion_keys

    def expand(self):
        return doot.locs[self.path]
