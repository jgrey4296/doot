#!/usr/bin/env python3
"""
  Injection adds to a task spec.
  allowing initial state, extra actions, etc.


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
from jgdv import Maybe
from jgdv.structs.strang import CodeReference
from jgdv.structs.chainguard import ChainGuard
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import Action_p
from doot.mixins.path_manip import PathManip_m
from doot.structs import DKey, TaskName, TaskSpec, DKeyed
from doot.mixins.injection import Injector_m

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

class JobInjector(Action_p, Injector_m):
    """
      Inject data into task specs.
      inject={copy=[Xs], expand={Yks : Yvs}, replace=[Zs]}
      'copy'   : redirects, and copies without further expansion : [a_,x] -> {a:2, x:{q}}
      'expand' : redirects, expands, then copies         : [a_,x] -> {a:2, x:5}
      'replace' sets keys to whatever replace value is passed in (for job.expand)

      X,Y can be lists or dicts, for simple setting, or remapping
      Z is just a straight list

    """

    @DKeyed.types("onto", "inject")
    def __call__(self, spec, state, onto, inject):
        injection = self.build_injection(spec, state, inject)
        match onto:
            case list():
                for x in onto:
                    x.model_extra.update(dict(**x.extra, **injection))
            case TaskSpec():
                onto.model_extra.update(dict(**x.extra, **injection))

    def build_injection(self, spec, state, inject, replacement=None, post:dict|None=None) -> Maybe[ChainGuard]:
        return super().build_injection(inject, spec, state, insertion=replacement)

class JobPrependActions(Action_p):

    @DKeyed.types("_onto", "add_actions")
    def __call__(self, spec, state, _onto, _actions):
        action_specs = [ActionSpec.build(x) for x in _actions]
        for x in _onto:
            actions = action_specs + x.actions
            x.actions = actions

class JobAppendActions(Action_p):

    @DKeyed.types("_onto", "add_actions")
    def __call__(self, spec, state, _onto, _actions):
        actions_specs = [ActionSpec.build(x) for x in _actions]
        for x in _onto:
            x.actions += action_specs

class JobInjectPathParts(PathManip_m):
    """
      Map lpath, fstem, fparent, fname, fext onto each
      taskspec in the `onto` list, using each spec's `key`
    """

    @DKeyed.types("onto", "roots")
    @DKeyed.redirects("key_")
    def __call__(self, spec, state, _onto, roots, _key):
        root_paths = self._build_roots(spec, state, roots)
        match _onto:
            case list():
                for x in _onto:
                    data = x.params
                    data.update(self._calc_path_parts(x.extra[_key], root_paths))
                    x.model_extra.update(data)
            case TaskSpec():
                data = dict(x.extra)
                data.update(self._calc_path_parts(onto.extra[_key], root_paths))
                _onto.model_extra.update(data)

class JobInjectShadowAction(PathManip_m):
    """
      Inject a shadow path into each task entry, using the target key which points to the relative path to shadow
      returns the *directory* of the shadow target
    """

    @DKeyed.types("onto")
    @DKeyed.paths("shadow_root")
    @DKeyed.redirects("key_")
    def __call__(self, spec, state, _onto, _shadow, _key):
        match _onto:
            case list():
                for x in _onto:
                    rel_path = self._shadow_path(x.extra[_key], _shadow)
                    x.model_extra.update(dict(**x.extra, **{"shadow_path": rel_path}))
            case TaskSpec():
                rel_path = self._shadow_path(onto.extra[_key], _shadow)
                onto.model_extra.update(dict(**onto.extra, **{"shadow_path": rel_path}))

class JobSubNamer(Action_p):
    """
      Apply the name {basename}.{i}.{key} to each taskspec in {onto}
    """

    @DKeyed.taskname
    @DKeyed.expands("keylit")
    @DKeyed.types("onto")
    def __call__(self, spec, state, _basename, _key, _onto):
        match _onto:
            case list():
                for i,x in enumerate(_onto):
                    val = x.extra[_key]
                    x.name = _basename.push(i, self._gen_subname(val))
            case TaskSpec():
                onto.name = _basename.push(self._gen_subname(val))

    def _gen_subname(self, val):
        match val:
            case pl.Path():
                return val.stem
            case str():
                return val
