#!/usr/bin/env python3
"""

"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import abc
import datetime
import enum
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.dkey import DKey
from jgdv.structs.locator import Location

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from .. import _interface as API  # noqa: N812
from .._interface import ArtifactStatus_e

if TYPE_CHECKING:
    from jgdv import Maybe, TimeDelta

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class TaskArtifact(Location):
    """
    A Location, but specialized to represent artifacts/files
      An concrete or abstract artifact a task can produce or consume.

      Tasks can depend on both concrete and abstract:
      depends_on=['file:>/a/file.txt', 'file:>*.txt', 'file:>?.txt']
      and can be a requirement for concrete or *solo* abstract artifacts:
      required_for=['file:>a/file.txt', 'file:>?.txt']

    """
    __slots__ = ("priority",)
    priority : int

    def __init__(self, *args:Any, **kwargs:Any) -> None:
        super().__init__(*args, **kwargs)
        self.priority = API.DEFAULT_PRIORITY

    def __bool__(self):
        return self.exists()

    @property
    def parent(self) -> pl.Path:
        return self.path.parent

    def is_stale(self, *, delta:Maybe[TimeDelta]=None) -> bool:
        """ whether the artifact itself is stale
        delta defaults to 1 day
        """
        match delta:
            case None:
                return self < datetime.timedelta(days=1)
            case datetime.timedelta():
                return self < delta
            case _:
                raise NotImplementedError()

    def reify(self, other:pl.Path|Location) -> Maybe[TaskArtifact]:
        """
        Apply a more concrete path onto this location
        """
        if self.is_concrete():
            raise NotImplementedError("Can't reify an already concrete location", self, other)

        match other:
            case pl.Path() | str():
                other = Location(other)
            case _:
                pass

        result   = []
        add_rest = False
        # Compare path
        for x,y in itz.zip_longest(self.body_parent, other.body_parent):
            if add_rest:
                result.append(y or x)
                continue
            match x, y:
                case _, None:
                    result.append(x)
                case None, _:
                    result.append(y)
                case _, _ if x == y:
                    result.append(x)
                case str() as x, _ if x == self.Wild.rec_glob:
                    add_rest = True
                    result.append(y)
                case str() as x, str() if x in self.Wild:
                    result.append(y)
                case str(), str() as y if y in self.Wild:
                    result.append(x)
                case str(), str():
                    return None

        logging.debug("%s and %s match on path", self, other)
        # Compare the stem/ext
        stem, ext = "", ""
        match self.stem, other.stem:
            case None, None:
                pass
            case None, str() as y:
                stem = y
            case str() as x, None:
                stem = x
            case str() as x, str() as y if x == y:
                stem = x
            case (xa, ya), (xb, yb) if xa == xb and ya == yb:
                stem = ya
            case (xa, ya), str() as xb:
                stem = xb
            case _, _:
                return None

        logging.debug("%s and %s match on stem", self, other)
        match self.ext(), other.ext():
            case None, None:
                pass
            case (xa, ya), (xb, yb) if xa == xb and ya == yb:
                ext = ya
            case (x, y), str() as yb:
                ext = yb
            case (_, x), None:
                ext = x
            case None, (_, y):
                ext = y
            case str() as x, None:
                ext = x
            case None, str() as y:
                ext = y
            case str() as x, str() as y if x == y:
                ext = x
            case _, _:
                return None

        logging.debug("%s and %s match", self, other)
        result.append(f"{stem}{ext}")

        return self.__class__("/".join(result))

    def exists(self) -> bool:
        as_path = self.path
        expanded = doot.locs[as_path] # type: ignore[attr-defined]
        return expanded.exists()

    def is_concrete(self) -> bool:
        if self.Marks.abstract in self:
            return False
        try:
            _ = doot.locs.expand(self) # type: ignore[attr-defined]
        except KeyError:
            return False
        else:
            return True


    def get_status(self) -> ArtifactStatus_e:
        """ Get the status of the artifact,
        To start, either declared,  or exists.
        TODO: add a stale check
        TODO: add a to-clean check
        """
        if self.exists():
            return ArtifactStatus_e.EXISTS


        return ArtifactStatus_e.DECLARED
