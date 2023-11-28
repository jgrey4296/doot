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
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import importlib
from tomler import Tomler
import doot.errors
import doot.constants
from doot.enums import TaskFlags, ReportEnum, StructuredNameEnum

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskFlags]

@dataclass
class DootTaskArtifact:
    """ Describes an artifact a task can produce or consume.
    Artifacts can be Definite (concrete path) or indefinite (glob path)
      TODO: make indefinite pattern paths
    """
    path : pl.Path = field()

    def __hash__(self):
        return hash(self.path)

    def __repr__(self):
        type = "Definite" if self.is_definite else "Indefinite"
        return f"<{type} TaskArtifact: {self.path.name}>"

    def __str__(self):
        return str(self.path)

    def __eq__(self, other:DootTaskArtifact|Any):
        match other:
            case DootTaskArtifact():
                return self.path == other.path
            case _:
                return False

    def __bool__(self):
        return self.exists

    @property
    def exists(self):
        return self.is_definite and self.path.exists()

    @property
    def is_definite(self):
        return self.path.stem not in "*?+"

    @property
    def is_stale(self) -> bool:
        """ whether the artifact itself is stale """
        return False

    def matches(self, other):
        """ match a definite artifact to its indefinite abstraction """
        match other:
            case DootTaskArtifact() if self.is_definite and not other.is_definite:
                parents_match = self.path.parent == other.path.parent
                exts_match    = self.path.suffix == other.path.suffix
                return parents_match and exts_match
            case _:
                raise TypeError(other)

"""

"""
