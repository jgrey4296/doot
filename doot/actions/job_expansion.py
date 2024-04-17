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
from doot.actions.job_injection import JobInjector

class JobGenerate(DootBaseAction):
    """ Run a custom function to generate task specs
      Function is in the form: fn(spec, state) -> list[DootTaskSpec]
    """

    @DootKey.dec.references("fn")
    @DootKey.dec.redirects("update_")
    def __call__(self, spec, state, _fn_ref, _update):
        fn = _fn_ref.try_import()
        return { _update : list(fn(spec, state)) }

class JobExpandAction(JobInjector):
    """
      Takes a template taskname/list[actionspec] and builds one new subtask for each entry in a list

      'inject' provides an injection dict, with $arg$ being the entry from the source list
    """

    @DootKey.dec.types("from", "inject", "template", "print_levels")
    @DootKey.dec.expands("prefix")
    @DootKey.dec.redirects("update_")
    @DootKey.dec.taskname
    def __call__(self, spec, state, _from, inject, template, _printL, prefix, _update, _basename):
        match prefix:
            case "{prefix}":
                prefix = "{Anon}"
            case _:
                pass

        result          = []
        build_queue     = []
        base_head       = _basename.task_head()
        actions, base   = self._prep_base(template)
        match _from:
            case int():
                build_queue += range(_from)
            case list():
                build_queue += _from
            case None:
                build_queue += [1]
            case _:
                printer.warning("Tried to expand a non-list of args")
                return self.ActRE.FAIL

        for i, arg in enumerate(build_queue):
                injection = self.build_injection(spec, state, inject, replacement=arg)
                new_spec  = DootTaskSpec.build(dict(name=_basename.subtask(prefix, i),
                                                    ctor=base,
                                                    actions = actions or [],
                                                    required_for=[base_head],
                                                    extra=injection,
                                                    print_levels=_printL or {},
                                                    ))
                result.append(new_spec)

        return { _update : result }

    def _prep_base(self, base:DootTaskName|list[DootActionSpec]) -> tuple[list, DootTaskName|None]:
        """
          base can be the literal name of a task (base="group::task") to build off,
          or an indirect key to a list of actions (base_="sub_actions")

          This handles those possibilities and returns a list of actions and maybe a task name

        """
        match base:
            case list():
                actions = base
                base    = None
            case DootTaskName():
                actions = []
            case str():
                actions = []
                base    = DootTaskName.build(base)
            case None:
                actions = []
                base    = None
            case _:
                raise doot.errors.DootActionError("Unrecognized base type", base)

        return actions, base

class JobMatchAction(DootBaseAction):
    """
      Take a mapping of {pattern -> task} and a list,
      and build a list of new subtasks

      use `prepfn` to get a value from a taskspec to match on.

      defaults to getting spec.extra.fpath.suffix
    """

    @DootKey.dec.types("onto_")
    @DootKey.dec.references("prepfn")
    @DootKey.dec.types("mapping")
    def __call__(self, spec, state, _onto, prepfn, mapping):
        match prepfn:
            case None:
                fn = lambda x: x.extra.fpath.suffix
            case DootCodeReference():
                fn = prepfn.try_import()

        for x in _onto:
            match fn(x):
                case str() as key if key in mapping:
                    x.ctor = DootTaskName.build(mapping[key])
                case _:
                    pass
