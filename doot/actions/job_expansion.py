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
from doot.actions.job_injection import JobInjector

class JobGenerate(Action_p):
    """ Run a custom function to generate task specs  """

    @DootKey.kwrap.references("fn")
    @DootKey.kwrap.redirects("update_")
    def __call__(self, spec, state, _fn_ref, _update):
        fn = _fn_ref.try_import()
        return { _update : list(fn(spec, state)) }

class JobExpandAction(JobInjector):
    """
      Takes a base action and builds one new subtask for each entry in a list

      'inject' provides an injection dict, with $arg$ being the entry from the source list
    """

    @DootKey.kwrap.types("from", "inject", "base", "print_levels")
    @DootKey.kwrap.expands("prefix")
    @DootKey.kwrap.redirects("update_")
    @DootKey.kwrap.taskname
    def __call__(self, spec, state, _from, inject, base, _printL, prefix, _update, _basename):
        result          = []
        actions, base   = self._prep_base(base)
        build_queue = []
        match _from:
            case int():
                build_queue += range(_from)
            case list():
                build_queue += _from
            case None:
                build_queue += [1]
            case _:
                printer.warning("Tried to expand a non-list of args")
                return None

        for i, arg in enumerate(build_queue):
                injection = self.build_injection(spec, state, inject, replacement=arg)
                new_spec  = DootTaskSpec.build(dict(name=_basename.subtask(prefix, i),
                                                    ctor=base,
                                                    actions = actions or [],
                                                    required_for=[_basename.task_head()],
                                                    extra=injection,
                                                    print_levels=_printL or {},
                                                    ))
                result.append(new_spec)


        return { _update : result }

    def _prep_base(self, base) -> tuple[list, DootTaskName|None]:
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
                    x.ctor = DootTaskName.build(mapping[key])
                case _:
                    pass
