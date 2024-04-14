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
printer = logmod.getLogger("doot._printer")
##-- end logging


import random
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.structs import DootKey, DootTaskSpec, DootTaskName, DootCodeReference
from doot.actions.base_action import DootBaseAction
from doot.actions.job_expansion import JobGenerate, JobExpandAction, JobMatchAction
from doot.actions.job_injection import JobPrependActions, JobAppendActions, JobInjector, JobInjectPathParts, JobInjectShadowAction, JobSubNamer
from doot.actions.job_queuing import JobQueueAction, JobQueueHead, JobChainer
from doot.mixins.path_manip import Walker_m


class JobWalkAction(Walker_m, DootBaseAction):
    """
      Triggers a directory walk to build tasks from
    """

    @DootKey.dec.types("roots", "exts")
    @DootKey.dec.types("recursive", hint={"type_": bool|None})
    @DootKey.dec.references("fn")
    @DootKey.dec.redirects("update_")
    def __call__(self, spec, state, roots, exts, recursive, fn, _update):
        exts    = {y for x in (exts or []) for y in [x.lower(), x.upper()]}
        rec     = recursive or False
        roots   = [DootKey.build(x).to_path(spec, state) for x in roots]
        match fn:
            case DootCodeReference():
                accept_fn = fn.try_import()
            case None:
                accept_fn = lambda x: True

        results = [x for x in self.walk_all(roots, exts, rec=rec, fn=accept_fn)]
        return { _update : results }

class JobLimitAction(DootBaseAction):
    """
      Limits a list to an amount, overwriting the 'from' key,
      'method' defaults to a random sample,
      or a coderef of type callable[[spec, state, list[taskspec]], list[taskspec]]

    """

    @DootKey.dec.types("from_", "count")
    @DootKey.dec.references("method")
    @DootKey.dec.redirects("from_")
    def __call__(self, spec, state, _from, count, method, _update):
        if count == -1:
            return

        match method:
            case None:
                limited = random.sample(_from, count)
            case DootCodeReference():
                fn      = method.try_import()
                limited = fn(spec, state, _from)

        return { _update : limited }
