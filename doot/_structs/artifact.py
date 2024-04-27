#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

import abc
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
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from pydantic import BaseModel, field_validator, model_validator, ValidationError
import importlib
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.enums import TaskFlags, ReportEnum, LocationMeta
from doot._structs.toml_loc import TomlLocation
from doot._structs.key import DootKey

class DootTaskArtifact(BaseModel, arbitrary_types_allowed=True):
    """
      Wraps a toml defined location into an artifact

      Describes an artifact a task can produce or consume.
    Artifacts can be Definite (concrete path) or indefinite (glob path)
    """
    base     : TomlLocation
    key      : DootKey

    _toml_str_prefix : ClassVar[str] = doot.constants.patterns.FILE_DEP_PREFIX
    _artifact_loc_key : ClassVar[str] = "!!Artifact!!"

    @staticmethod
    def build(data:str|dict|pl.Path) -> DootTaskArtifact:
        """
        build an artifact using a str|path of a path,
        or a dict setting a path and metadata
        """
        match data:
            case str() if data.startswith(DootTaskArtifact._toml_str_prefix):
                # prefixed str: file:>a/simple/path.txt
                base = TomlLocation.build(DootTaskArtifact._artifact_loc_key, data.removeprefix(DootTaskArtifact._toml_str_prefix))
                base.meta |= LocationMeta.file
                key = DootKey.build(base.base)
            case str():
                # a straight string, no extra metadata
                # infers indefinite
                base = TomlLocation.build(DootTaskArtifact._artifact_loc_key, data)
                key  = DootKey.build(base.base)
            case dict():
                # dict with metadata
                base = TomlLocation.build(DootTaskArtifact._artifact_loc_key, data)
                key = DootKey.build(base.base)
            case pl.Path():
                # path, no metadata, infers indefinite
                base = TomlLocation.build(DootTaskArtifact._artifact_loc_key, data)
                key = DootKey.build(base.base)
            case _:
                raise TypeError("Unknown Type to build Artifact from: %s", data)

        return DootTaskArtifact(base=base, key=key)

    def __repr__(self):
        return f"<TaskArtifact: {self.key} : {self.base.meta}>"

    def __str__(self):
        return str(self.base.base)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other:DootTaskArtifact|Any):
        match other:
            case DootTaskArtifact():
                return self.base == other.base
            case _:
                return False

    def __bool__(self):
        return self.exists

    def __contains__(self, other):
        """ whether a definite artifact is matched by self, an indefinite artifact
          a/b/c.py ∈ a/b/*.py
          ________ ∈ a/*/c.py
          ________ ∈ a/b/c.*
          ________ ∈ a/*/c.*
          ________ ∈ **/c.py

        """
        if not self.check(LocationMeta.indefinite):
            return False

        for x,y in zip(self.parent.parts, other.parent.parts):
            if x == "**" or y == "**":
                break
            if x == "*" or y == "*":
                continue
            if x != y:
                return False

        suffix      = (not self._definite_suffix) or self.base.base.suffix == other.base.base.suffix
        stem        = (not self._definite_stem)    or self.base.base.stem == other.base.base.stem
        return  suffix and stem

    @property
    def exists(self):
        if not self.is_definite:
            return False
        as_path = self.key.to_path(None, None)
        return as_path.exists()

    @property
    def is_definite(self):
        """ tests the entire artifact path """
        return not self.check(LocationMeta.indefinite)

    @property
    def _definite_stem(self):
        """ tests the stem of the artifact """
        return "*" not in self.base.base.stem

    @property
    def _definite_suffix(self):
        """ tests the suffix of the artifact """
        return "*" not in self.base.base.suffix

    @property
    def parent(self):
        return self.base.base.parent

    def is_stale(self) -> bool:
        """ whether the artifact itself is stale """
        raise NotImplementedError('TODO')

    def check(self, meta:LocationMeta) -> bool:
        return self.base.check(meta)
