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

class JobQueueAction(Action_p):
    """
      Queues a list of tasks into the tracker.
      Args are strings converted to simple taskspec's
      `from` is a state list of DootTaskSpec's
    """

    @DootKey.kwrap.args
    @DootKey.kwrap.types("from_", hint={"type_":list|DootTaskSpec|None})
    @DootKey.kwrap.basename
    def __call__(self, spec, state, _args, _from, _basename):
        subtasks  = []
        subtasks += [DootTaskSpec(_basename.subtask(i), ctor=DootTaskName.from_str(x), required_for=[_basename.task_head()]) for i,x in enumerate(_args)]

        match _from:
            case [*xs] if all(isinstance(x, DootTaskSpec) for x in xs):
                subtasks += xs
            case DootTaskSpec():
                subtasks.append(_from)
            case None:
                pass
            case _:
                raise doot.errors.DootActionError("Tried to queue a not DootTaskSpec")

        return subtasks

class JobSubNamer(Action_p):
    """
      Apply the name {basename}.{i}.{key} to each taskspec in {onto}
    """

    @DootKey.kwrap.basename
    @DootKey.kwrap.expands("key")
    @DootKey.kwrap.types("onto")
    def __call__(self, spec, state, _basename, key, _onto):
        for x in enumerate(_onto):
            match x:
                case DootTaskSpec():
                    x.name = _basename.subtask(i, key)
                case _:
                    raise doot.errors.DootActionError("Job Tried to apply a name to a non-taskspec", x)

class JobExpandAction(Action_p):
    """
      Takes a base action and builds one new subtask for each entry in a list

      'inject' either:
      provides an injection dict, with $arg$ being the entry from the source list, or
      provides a key to assign the entry from the source list
    """

    @DootKey.kwrap.types("from", "inject")
    @DootKey.kwrap.expands("base")
    @DootKey.kwrap.redirects("update_")
    @DootKey.kwrap.basename
    def __call__(self, spec, state, _from, inject, base, _update, _basename):
        result         = []
        base           = DootTaskName.from_str(base)
        inject_base    = {}
        inject_arg_key = []
        match inject:
             case dict() | TomlGuard():
                 inject_base.update(inject)
                 inject_arg_key = [k for k,v in inject.items() if v == doot.constants.patterns.STATE_ARG_EXPANSION]
             case str():
                 inject_arg_key = [inject]

        match _from:
            case list():
                for i, arg in enumerate(_from):
                    injection = {}
                    injection.update(inject_base)
                    injection.update({k:arg for k in inject_arg_key})
                    result.append(DootTaskSpec(_basename.subtask(i),
                                               ctor=base,
                                               required_for=[_basename.task_head()],
                                               extra=injection
                                  ))
            case dict() | TomlGuard():
                injection = {}
                injection.update(_from)
                injection.update(inject_base)
                injection.update({k:arg for k in inject_arg_key})
                result.append(DootTaskSpec(_basename.subtask(i),
                                           ctor=base,
                                           required_for=[_basename.task_head()],
                                           extra=injection
                              ))
            case _:
                printer.warning("Tried to expand a non-list of args")

        return { _update : result }

class JobMatchAction(Action_p):
    """
      Take a mapping of {pattern -> task} and a list,
      and build a list of new subtasks

      use `prepfn` to get a value from a taskspec to match on.

      defaults to getting spec.extra.fpath.suffix
    """

    @DootKey.kwrap.types("onto_")
    @DootKey.kwrap.references("prepfn")
    @DootKey.kwrap.types("mapping")
    def __call__(self, spec, state, _onto, prepfn, mapping):
        match prepfn:
            case None:
                fn = lambda x: x.extra.fpath.suffix
            case DootCodeReference():
                fn = prepfn.try_import()

        for x in _onto:
            match fn(x):
                case str() as key if key in mapping:
                    x.ctor = DootTaskName.from_str(mapping[key])
                case _:
                    pass

class JobWalkAction(Action_p):
    """
      Triggers a directory walk to build tasks from
    """

    @DootKey.kwrap.types("roots", "exts")
    @DootKey.kwrap.types("recursive", hint={"type": bool|None})
    @DootKey.kwrap.references("fn")
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, roots, exts, recursive, fn, _update):
        exts    = {y for x in exts for y in [x.lower(), x.upper()]}
        rec     = recursive or False
        roots   = [DootKey.make(x).to_path(spec, state) for x in roots]
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
        check_fn = lambda x: (fn(x) not in [None, False, _WalkControl.no, _WalkControl.noBut]
                              and x.name not in walk_ignores
                              and (not bool(exts) or (x.is_file() and x.suffix in exts)))

        if check_fn(target):
            yield target

        if not target.is_dir():
            return None

        for x in target.iterdir():
            if check_fn(x):
                yield x

class JobLimitAction(Action_p):
    """
      Limits a list to an amount
    """

    @DootKey.kwrap.types("from_", "count")
    @DootKey.kwrap.references("method")
    @DootKey.kwrap.redirects("from_")
    def __call__(self, spec, state, _from, count, method, _update):
        match method:
            case None:
                limited = random.sample(_from, count)
            case DootCodeReference():
                fn      = method.try_import()
                limited = fn(spec, state, _from, count)

        return { update : limited }

class JobPrependActions(Action_p):

    @DootKey.kwrap.types("_onto", "add_actions")
    def __call__(self, spec, state, _onto, _actions):
        for x in _onto:
            actions = _actions + x.actions
            x.actions = actions

class JobAppendActions(Action_p):

    @DootKey.kwrap.types("_onto", "add_actions")
    def __call__(self, spec, state, _onto, _actions):
        for x in _onto:
            x.actions += _actions

class JobInjectAction(Action_p):

    @DootKey.kwrap.types("onto", "inject")
    def __call__(self, spec, state, _onto, inject):
        for x in _onto:
            base = dict(x.extra.items())
            base.update(inject)
            x.extra = base

class _RelPather(Action_p):

    def _rel_path(self, fpath, roots) -> pl.Path:
        """
        make the path relative to the appropriate root
        """
        for root in roots:
            try:
                return fpath.relative_to(root)
            except ValueError:
                continue

        raise ValueError(f"{fpath} is not able to be made relative")

class JobInjectPathParts(_RelPather):
    """
      Map lpath, fstem, fparent, fname, fext onto each
      taskspec in the `onto` list, using each spec's `key`
    """

    @DootKey.kwrap.types("onto", "roots")
    @DootKey.kwrap.expands("key")
    def __call__(self, spec, state, _onto, roots, key):
        for x in _onto:
            base_extra            = dict(x.extra.items())
            fpath                 = x.extra[key]
            base_extra['lpath']   = self._rel_path(fpath, roots)
            base_extra['fstem']   = fpath.stem
            base_extra['fparent'] = fpath.parent
            base_extra['fname']   = fpath.name
            base_extra['fext']    = fpath.suffix

class JobInjectShadowAction(_RelPather):
    """
      Inject a shadow path into each task entry
    """

    def _shadow_path(self, fpath:pl.Path, roots:list, shadow_root:pl.Path) -> pl.Path:
        shadow_root = doot.locs[self.spec.extra.shadow_root]
        rel_path    = self._rel_path(fpath, roots)
        result      = shadow_root / rel_path
        if result == fpath:
            raise doot.errors.DootLocationError("Shadowed Path is same as original", fpath)

        return result.parent

    @DootKey.kwrap.types("onto", "roots")
    @DootKey.kwrap.paths("shadow_root")
    def __call__(self, spec, state, _onto, roots, _shadow):
        for x in _onto:
            rel_path = self._shadow_path(x.extra.fpath, roots, _shadow)
