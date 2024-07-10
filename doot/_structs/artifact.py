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
from doot.enums import TaskMeta_f, Report_f, LocationMeta_f
from doot._structs.location import Location, GLOB, SOLO, REC_GLOB
from doot._structs.dkey import DKey

class TaskArtifact(Location, arbitrary_types_allowed=True):
    """
      An concrete or abstract artifact a task can produce or consume.

      Tasks can depend on both concrete and abstract:
      depends_on=['file:>/a/file.txt', 'file:>*.txt', 'file:>?.txt']
      and can be a requirement for concrete or *solo* abstract artifacts:
      required_for=['file:>a/file.txt', 'file:>?.txt']


    """

    priority : int = 10

    def __repr__(self):
        return f"<TaskArtifact: {self.path} : {self.meta}>"

    def __str__(self):
        return str(self.path)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other:str|pl.Path|TaskArtifact|Any):
        match other:
            case str() | pl.Path():
                return pl.Path(other) == self.path
            case TaskArtifact():
                return self.path == other.path
            case _:
                return False

    def __bool__(self):
        return self.exists()

    @ftz.cached_property
    def is_concrete(self):
        return not self.check(LocationMeta_f.abstract)

    @ftz.cached_property
    def parent(self):
        return self.path.parent

    def is_stale(self) -> bool:
        """ whether the artifact itself is stale """
        raise NotImplementedError('TODO')


    def match_with(self, other:pl.Path|TaskArtifact) -> None|TaskArtifact:
        """ An abstract location, given a concrete other location,
          will apply parts of it onto itself, where it has wildcards

          To match, the stem *must* be a wildcard, at least.

          This is for instantiating task transformers.

          eg: a/*/?.blah + a/blah/file.txt -> a/blah/file.blah
          a/**/?.blah + a/b/c/d.txt -> a/b/c/d.blah

        """
        if LocationMeta_f.abstract not in self:
            return None

        a_path, a_stem, a_suff = self.abstracts

        if not a_stem:
            return None

        match other:
            case Location():
                match_on = other.path.parent.parts
                stem     = other.path.stem
                suff     = other.path.suffix
            case pl.Path():
                match_on = other.parent.parts
                stem     = other.stem
                suffix   = other.suffix
            case _:
                raise ValueError("Location can't match against a non-Location or path", other)

        result = []
        rest_of = False

        if a_path:
            for i, (x,y) in enumerate(zip(self.path.parent.parts, match_on)):
                if x in [GLOB, SOLO]:
                    result.append(y)
                elif x == REC_GLOB:
                    result += match_on[i:]
                elif x == y:
                    result.append(x)
                else:
                    return None
        else:
            result += self.path.parents

        result.append(stem)

        base = pl.Path().joinpath(*result)
        if a_suff:
            return TaskArtifact(path=base.with_suffix(suffix),
                                    key=self.key)

        return TaskArtifact(path=base.with_suffix(self.path.suffix),
                                key=self.key)
