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

import random
from tomlguard import TomlGuard
import doot
import doot.errors
from doot._abstract import Action_p
from doot.structs import DootKey, DootTaskSpec, DootTaskName, DootCodeReference
from doot.actions.job_expansion import JobGenerate, JobExpandAction, JobMatchAction
from doot.actions.job_injection import JobPrependActions, JobAppendActions, JobInjectAction, JobInjectPathParts, JobInjectShadowAction, JobSubNamer
from doot.actions.job_queuing import JobQueueAction, JobQueueHead, JobChainer

walk_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).settings.walking.ignores()
walk_halts   : Final[str]  = doot.config.on_fail([".doot_ignore"], list).settings.walking.halts()

class _WalkControl(enum.Enum):
    """
    accept  : is a result, and descend if recursive
    keep    : is a result, don't descend
    discard : not a result, descend
    reject  : not a result, don't descend
    """
    yesAnd  = enum.auto()
    yes     = enum.auto()
    noBut   = enum.auto()
    no      = enum.auto()

class JobWalkAction(Action_p):
    """
      Triggers a directory walk to build tasks from
    """

    @DootKey.kwrap.types("roots", "exts")
    @DootKey.kwrap.types("recursive", hint={"type_": bool|None})
    @DootKey.kwrap.references("fn")
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, roots, exts, recursive, fn, _update):
        exts    = {y for x in (exts or []) for y in [x.lower(), x.upper()]}
        rec     = recursive or False
        roots   = [DootKey.build(x).to_path(spec, state) for x in roots]
        match fn:
            case DootCodeReference():
                accept_fn = fn.try_import()
            case None:
                accept_fn = lambda x: True

        results = [x for x in self.walk_all(spec, state, roots, exts, rec=rec, fn=accept_fn)]
        return { _update : results }

    def walk_all(self, spec, state, roots, exts, rec=False, fn=None) -> Generator[dict]:
        """
        walk all available targets,
        and generate unique names for them
        """
        result = []
        match rec:
            case True:
                for root in roots:
                    result += self.walk_target_deep(root, exts, fn)
            case False:
                for root in roots:
                    result += self.walk_target_shallow(root, exts, fn)

        return result

    def walk_target_deep(self, target, exts, fn) -> Generator[pl.Path]:
        printer.info("Walking Target: %s : exts=%s", target, exts)
        if not target.exists():
            return None

        queue = [target]
        while bool(queue):
            current = queue.pop()
            if not current.exists():
                continue
            if current.name in walk_ignores:
                continue
            if current.is_dir() and any([(current / x).exists() for x in walk_halts]):
                continue
            if bool(exts) and current.is_file() and current.suffix not in exts:
                continue
            match fn(current):
                case _WalkControl.yes:
                    yield current
                case True if current.is_dir():
                    queue += sorted(current.iterdir())
                case True | _WalkControl.yesAnd:
                    yield current
                    if current.is_dir():
                        queue += sorted(current.iterdir())
                case False | _WalkControl.noBut if current.is_dir():
                    queue += sorted(current.iterdir())
                case None | False:
                    continue
                case _WalkControl.no | _WalkControl.noBut:
                    continue
                case _ as x:
                    raise TypeError("Unexpected filter value", x)

    def walk_target_shallow(self, target, exts, fn):
        if target.is_file():
            fn_fail = fn(target) in [None, False, _WalkControl.no, _WalkControl.noBut]
            ignore  = target.name in walk_ignores
            bad_ext = (bool(exts) and (x.is_file() and x.suffix in exts))
            if not (fn_fail or ignore or bad_ext):
                yield target
            return None

        for x in target.iterdir():
            fn_fail = fn(x) in [None, False, _WalkControl.no, _WalkControl.noBut]
            ignore  = x.name in walk_ignores
            bad_ext = bool(exts) and x.is_file() and x.suffix not in exts
            if not (fn_fail or ignore or bad_ext):
                yield x

class JobLimitAction(Action_p):
    """
      Limits a list to an amount, overwriting the 'from' key,
      'method' defaults to a random sample,
      or a coderef of type callable[[spec, state, list[taskspec]], list[taskspec]]

    """

    @DootKey.kwrap.types("from_", "count")
    @DootKey.kwrap.references("method")
    @DootKey.kwrap.redirects("from_")
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
