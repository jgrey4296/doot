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

import importlib
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.enums import TaskFlags, ReportEnum

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskFlags]

@dataclass
class DootTaskArtifact:
    """ Describes an artifact a task can produce or consume.
    Artifacts can be Definite (concrete path) or indefinite (glob path)
      TODO: make indefinite pattern paths
    """
    path : pl.Path = field()

    _basic_str : str = field(init=False)

    def __post_init__(self):
        self._basic_str = str(self.path)
        self.path = doot.locs[self.path]

    def __hash__(self):
        return hash(self.path)

    def __repr__(self):
        type = "Definite" if self.is_definite else "Indefinite"
        return f"<{type} TaskArtifact: {self.path.name}>"

    def __str__(self):
        return self._basic_str

    def __eq__(self, other:DootTaskArtifact|Any):
        match other:
            case DootTaskArtifact():
                return self.path == other.path
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
        for x,y in zip(self.path.parent.parts, other.path.parent.parts):
            if x == "**" or y == "**":
                break
            if x == "*" or y == "*":
                continue
            if x != y:
                return False

        suffix      = (not self._dsuffix) or self.path.suffix == other.path.suffix
        stem        = (not self._dstem)    or self.path.stem == other.path.stem
        return  suffix and stem

    @property
    def exists(self):
        return self.path.exists() or not self.is_definite

    @property
    def is_definite(self):
        """ tests the entire artifact path """
        return "*" not in str(self.path)

    @property
    def _dstem(self):
        """ tests the stem of the artifact """
        return "*" not in self.path.stem

    @property
    def _dsuffix(self):
        """ tests the suffix of the artifact """
        return "*" not in self.path.suffix

    @property
    def is_stale(self) -> bool:
        """ whether the artifact itself is stale """
        raise NotImplementedError('TODO')
