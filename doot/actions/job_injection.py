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
        injection = self.build_injection(spec, state, inject)
        match onto:
            case list():
                for x in onto:
                    x.extra = TomlGuard(dict(**x.extra, **injection))
            case DootTaskSpec():
                onto.extra = TomlGuard(dict(**x.extra, **injection))

    def build_injection(self, spec, state, inject, replacement=None, post:dict|None=None) -> None|TomlGuard:
        match inject:
            case dict():
                copy    = inject.get("copy", [])
                expand  = inject.get("expand", {})
                replace = inject.get("replace", [])
            case TomlGuard():
                copy    = inject.on_fail([], non_root=True).copy()
                expand  = inject.on_fail({}, non_root=True).expand()
                replace = inject.on_fail([], non_root=True).replace()
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
                    as_key = DootKey.build(v)
                    injection_dict[k] = as_key.basic(spec, state)
            case list():
                for k in copy:
                    as_key = DootKey.build(k)
                    injection_dict[as_key.direct] = as_key.redirect(spec).basic(spec, state)

        match expand:
            case dict():
                for k,v in expand.items():
                    as_key = DootKey.build(v)
                    injection_dict[k] = as_key.to_type(spec, state)
            case list():
                for k in expand:
                    as_key = DootKey.build(k)
                    injection_dict[as_key.direct] = as_key.to_type(spec, state)

        if replacement is not None:
            injection_dict.update({k:replacement for k in replace})

        if post is not None:
            injection_dict.update({k:v for k,v in post.items() if v is not None})

        return injection_dict

class JobPrependActions(Action_p):

    @DootKey.kwrap.types("_onto", "add_actions")
    def __call__(self, spec, state, _onto, _actions):
        action_specs = [DootActionSpec.build(x) for x in _actions]
        for x in _onto:
            actions = action_specs + x.actions
            x.actions = actions

class JobAppendActions(Action_p):

    @DootKey.kwrap.types("_onto", "add_actions")
    def __call__(self, spec, state, _onto, _actions):
        actions_specs = [DootActionSpec.build(x) for x in _actions]
        for x in _onto:
            x.actions += action_specs

class JobInjectPathParts(Action_p):
    """
      Map lpath, fstem, fparent, fname, fext onto each
      taskspec in the `onto` list, using each spec's `key`
    """

    @DootKey.kwrap.types("onto", "roots")
    @DootKey.kwrap.redirects("key")
    def __call__(self, spec, state, _onto, roots, key):
        root_paths = self._build_roots(spec, state, roots)
        match _onto:
            case list():
                for x in _onto:
                    x.extra = self._calc_path_parts(x.extra, key, root_paths)
            case DootTaskSpec():
                onto.extra = self._calc_path_parts(onto.extra, key, roots)

    def _calc_path_parts(self, data, key, roots) -> TomlGuard:
        fpath                  = data[key]
        assert(fpath is not None)
        path_extras            = dict(data)
        path_extras['lpath']   = self._get_relative(fpath, roots)
        path_extras['fstem']   = fpath.stem
        path_extras['fparent'] = fpath.parent
        path_extras['fname']   = fpath.name
        path_extras['fext']    = fpath.suffix
        path_extras['pstem']   = fpath.parent.stem
        return TomlGuard(path_extras)

    def _build_roots(self, spec, state, roots) -> list[pl.Path]:
        """
        build the path relative to the appropriate root
        """
        results = []
        if roots is None:
            return results

        for root in roots:
            root_key = DootKey.build(root)
            results.append(root_key.to_path(spec, state))

        return results

    def _get_relative(self, fpath, roots) -> pl.Path:
        for root_path in roots:
            try:
                return fpath.relative_to(root_path)
            except ValueError:
                continue

        raise ValueError(f"{fpath} is not able to be made relative")

class JobInjectShadowAction(Action_p):
    """
      Inject a shadow path into each task entry, using the target key which points to the relative path to shadow
      returns the *directory* of the shadow target
    """

    @DootKey.kwrap.types("onto")
    @DootKey.kwrap.paths("shadow_root")
    @DootKey.kwrap.expands("key")
    def __call__(self, spec, state, _onto, _shadow, key):
        match _onto:
            case list():
                for x in _onto:
                    rel_path = self._shadow_path(x.extra[key], _shadow)
                    x.extra = TomlGuard(dict(**x.extra, **{"shadow_path": rel_path}))
            case DootTaskSpec():
                rel_path = self._shadow_path(onto.extra[key], _shadow)
                onto.extra = TomlGuard(dict(**onto.extra, **{"shadow_path": rel_path}))

    def _shadow_path(self, lpath:pl.Path, shadow_root:pl.Path) -> pl.Path:
        assert(isinstance(lpath, pl.Path))
        assert(not lpath.is_absolute())
        result      = shadow_root / lpath
        if result == doot.locs[lpath]:
            raise doot.errors.DootLocationError("Shadowed Path is same as original", fpath)

        return result.parent

class JobSubNamer(Action_p):
    """
      Apply the name {basename}.{i}.{key} to each taskspec in {onto}
    """

    @DootKey.kwrap.taskname
    @DootKey.kwrap.expands("key")
    @DootKey.kwrap.types("onto")
    def __call__(self, spec, state, _basename, key, _onto):
        match _onto:
            case list():
                for i,x in enumerate(_onto):
                    val = x.extra[key]
                    x.name = _basename.subtask(i, self._gen_subname(val))
            case DootTaskSpec():
                onto.name = _basename.subtask(self._gen_subname(val))

    def _gen_subname(self, val):
        match val:
            case pl.Path():
                return val.stem
            case str():
                return val
