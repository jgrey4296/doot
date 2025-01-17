#!/usr/bin/env python3
"""


"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import random
import re
import time
import types
import weakref
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.strang import CodeReference

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.actions.base_action import DootBaseAction
from doot.mixins.path_manip import Walker_m
from doot.structs import DKey, TaskName, TaskSpec, DKeyed

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

class JobWalkAction(Walker_m, DootBaseAction):
    """
      Triggers a directory walk to build tasks from

      starts at each element in `roots`,
      files must match with a suffix in `exts`, if bool(exts)
      potential files are used that pass `fn`,
    """

    @DKeyed.types("roots", "exts")
    @DKeyed.types("recursive", check=bool|None, fallback=False)
    @DKeyed.references("fn")
    @DKeyed.redirects("update_")
    def __call__(self, spec, state, roots, exts, recursive, fn, _update):
        exts    = {y for x in (exts or []) for y in [x.lower(), x.upper()]}
        rec     = recursive or False
        roots   = [DKey(x, mark=DKey.mark.PATH).expand(spec, state) for x in roots]
        match fn:
            case CodeReference():
                match fn():
                    case ImportError() as err:
                        raise err
                    case x:
                        accept_fn = x
            case None:
                def accept_fn(x):
                    return True

        results = [x for x in self.walk_all(roots, exts, rec=rec, fn=accept_fn)]
        return { _update : results }

class JobLimitAction(DootBaseAction):
    """
      Limits a list to an amount, overwriting the 'from' key,
      'method' defaults to a random sample,
      or a coderef of type callable[[spec, state, list[taskspec]], list[taskspec]]

    """

    @DKeyed.types("count")
    @DKeyed.references("method")
    @DKeyed.redirects("from_")
    def __call__(self, spec, state, count, method, _update):
        if count == -1:
            return

        _from = _update.expand(spec, state)
        match method:
            case None:
                limited = random.sample(_from, count)
            case CodeReference():
                fn      = method()
                limited = fn(spec, state, _from)

        return { _update : limited }
