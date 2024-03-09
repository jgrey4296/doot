#!/usr/bin/env python3
"""
  Injection adds to a task spec.
  allowing initial state, extra actions, etc.



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


class _RelPather(Action_p):

    def _rel_path(self, spec, state, fpath, roots) -> pl.Path:
        """
        make the path relative to the appropriate root
        """
        for root in roots:
            root_key = DootKey.make(root)
            root_path = root_key.to_path(spec, state)
            try:
                return fpath.relative_to(root_path)
            except ValueError:
                continue

        raise ValueError(f"{fpath} is not able to be made relative")

class JobInjector(Action_p):
    """
      Inject data into task specs.
      "inject" = {copy=X, expand=Y, replace=Z}
      'copy'   : redirects, and copies without expansion : [a_,x] -> {a:2, x:{q}}
      'expand' : redirects, expands, then copies         : [a_,x] -> {a:2, x:5}
      'replace' sets keys to whatever replace value is passed in (for job.expand)

      X,Y can be lists or dicts, for simple setting, or remapping
      Z is just a straight list

    """

    @DootKey.kwrap.types("onto", "inject")
    def __call__(self, spec, state, onto, inject):
        self.apply_injection(spec, state, onto, inject)

    def build_injection(self, spec, state, inject, replacement=None, post:dict|None=None) -> None|TomlGuard:
        match inject:
            case dict():
                copy    = inject.get("copy", [])
                expand  = inject.get("expand", {})
                replace = inject.get("replace", [])
            case TomlGuard():
                copy    = inject.on_fail([]).copy()
                expand  = inject.on_fail({}).expand()
                replace = inject.on_fail([]).replace()
            case None:
                return
            case _:
                raise doot.errors.DootActionError("Wrong format to state inject, should be {copy=[], expand=[]}")

        if isinstance(replace, dict):
            raise doot.errors.DootActionError("wrong format for replacement injection, should be a list of keys")

        injection_dict = {}

        match copy:
            case dict():
                for k,v in copy.items():
                    as_key = DootKey.make(v)
                    injection_dict[k] = as_key.basic(spec, state)
            case list():
                for k in copy:
                    as_key = DootKey.make(k)
                    injection_dict[as_key.direct] = as_key.redirect(spec).basic(spec, state)

        match expand:
            case dict():
                for k,v in expand.items():
                    as_key = DootKey.make(v)
                    injection_dict[k] = as_key.to_type(spec, state)
            case list():
                for k in expand:
                    as_key = DootKey.make(k)
                    injection_dict[as_key.direct] = as_key.to_type(spec, state)

        if replacement is not None:
            injection_dict.update({k:replacement for k in replace})

        if post is not None:
            injection_dict.update({k:v for k,v in post.items() if v is not None})

        return injection_dict

class JobPrependActions(Action_p):

    @DootKey.kwrap.types("_onto", "add_actions")
    def __call__(self, spec, state, _onto, _actions):
        action_specs = [DootActionSpec.from_data(x) for x in _actions]
        for x in _onto:
            actions = action_specs + x.actions
            x.actions = actions

class JobAppendActions(Action_p):

    @DootKey.kwrap.types("_onto", "add_actions")
    def __call__(self, spec, state, _onto, _actions):
        actions_specs = [DootActionSpec.from_data(x) for x in _actions]
        for x in _onto:
            x.actions += action_specs

class JobInjectAction(Action_p):

    @DootKey.kwrap.types("onto", "inject")
    def __call__(self, spec, state, _onto, inject):
        for x in _onto:
            x.extra = TomlGuard(dict(**x.extra, **inject))

class JobInjectPathParts(_RelPather):
    """
      Map lpath, fstem, fparent, fname, fext onto each
      taskspec in the `onto` list, using each spec's `key`
    """

    @DootKey.kwrap.types("onto", "roots")
    @DootKey.kwrap.expands("key")
    def __call__(self, spec, state, _onto, roots, key):
        for x in _onto:
            fpath                  = x.extra[key]
            path_extras            = dict(x.extra)
            path_extras['lpath']   = self._rel_path(spec, state, fpath, roots)
            path_extras['fstem']   = fpath.stem
            path_extras['fparent'] = fpath.parent
            path_extras['fname']   = fpath.name
            path_extras['fext']    = fpath.suffix
            path_extras['pstem']   = fpath.parent.stem
            x.extra                = TomlGuard(path_extras)

class JobInjectShadowAction(_RelPather):
    """
      Inject a shadow path into each task entry
    """

    def _shadow_path(self, fpath:pl.Path, roots:list, shadow_root:pl.Path) -> pl.Path:
        shadow_root = doot.locs[self.spec.extra.shadow_root]
        rel_path    = self._rel_path(spec, state, fpath, roots)
        result      = shadow_root / rel_path
        if result == fpath:
            raise doot.errors.DootLocationError("Shadowed Path is same as original", fpath)

        return result.parent

    @DootKey.kwrap.types("onto", "roots")
    @DootKey.kwrap.paths("shadow_root")
    def __call__(self, spec, state, _onto, roots, _shadow):
        for x in _onto:
            rel_path = self._shadow_path(x.extra.fpath, roots, _shadow)
            x.extra = TomlGuard(dict(**x.extra, **{"shadow_path": rel_path}))

class JobSubNamer(Action_p):
    """
      Apply the name {basename}.{i}.{key} to each taskspec in {onto}
    """

    @DootKey.kwrap.taskname
    @DootKey.kwrap.expands("key")
    @DootKey.kwrap.types("onto")
    def __call__(self, spec, state, _basename, key, _onto):
        for x in enumerate(_onto):
            match x:
                case DootTaskSpec():
                    x.name = _basename.subtask(i, key)
                case _:
                    raise doot.errors.DootActionError("Job Tried to apply a name to a non-taskspec", x)
