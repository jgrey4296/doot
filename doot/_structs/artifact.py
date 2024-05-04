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

from pydantic import BaseModel, field_validator, model_validator
import importlib
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.enums import TaskFlags, ReportEnum, LocationMeta
from doot._structs.location import Location
from doot._structs.key import DootKey

class DootTaskArtifact(Location, arbitrary_types_allowed=True):
    """
      An concrete or abstract artifact a task can produce or consume.

    """

    def __repr__(self):
        return f"<TaskArtifact: {self.key} : {self.meta}>"

    def __str__(self):
        return str(self.path)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other:DootTaskArtifact|Any):
        match other:
            case DootTaskArtifact():
                return self.path == other.path
            case _:
                return False

    def __bool__(self):
        return self.exists

    @property
    def is_concrete(self):
        return not self.check(LocationMeta.abstract)

    @property
    def parent(self):
        return self.path.parent

    def is_stale(self) -> bool:
        """ whether the artifact itself is stale """
        raise NotImplementedError('TODO')
