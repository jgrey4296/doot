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
# from dataclasses import InitVar, dataclass, field
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

printer = logmod.getLogger("doot._printer")

import doot
import doot.errors
from doot._abstract import Action_p
from doot.structs import DootKey

class JobQueueAction(Action_p):
    """
      Queues a list of tasks into the tracker
    """

    @DootKey.kwrap.types("from_", hint={"type_":list})
    def __call__(self, spec, state, _from):

        return _from


class JobWalkAction(Action_p):
    """
      Triggers a directory walk to build tasks from
    """

    @DootKey.kwrap.types("roots", "exts", "recursive")
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, roots, exts, recursive, _update):
        pass


class JobLimitAction(Action_p):
    """
      Limits a list to an amount
    """

    @DootKey.kwrap.types("from_", "count")
    @DootKey.kwrap.types("method")
    @DootKey.kwrap.redirects("from_")
    def __call__(self, spec, state, count, _from, method, _update):

        return { update : limited }


class JobExpandAction(Action_p):
    """
      Takes a base action and builds one new subtask for each entry in a list
    """

    @DootKey.kwrap.types("from_")
    @DootKey.kwrap.expands("base")
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, _from, base, _update):
        pass


class JobMatchAction(Action_p):
    """
      Take a mapping of {pattern -> task} and a list,
      and build a list of new subtasks
    """

    @DootKey.kwrap.types("from_")
    @DootKey.kwrap.types("mapping")
    @DootKey.kwrap.redirects("from_")
    def __call__(self, spec, state, _from, mapping, _update):

        return { _update : _from }


class JobInjectShadowAction(Action_p):
    """
      Inject a shadow path into each task entry
    """

    def _shadow_path(self, fpath:pl.Path) -> pl.Path:
        shadow_root = doot.locs[self.spec.extra.shadow_root]
        rel_path    = self.rel_path(fpath)
        result      = shadow_root / rel_path
        if result == fpath:
            raise doot.errors.DootLocationError("Shadowed Path is same as original", fpath)

        return result.parent

    @DootKey.kwrap.types("from_")
    @DootKey.kwrap.redirects("from_")
    def __call__(self, spec, state, _from, _update):

        return { _update : _from }
