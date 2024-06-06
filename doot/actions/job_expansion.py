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
from doot.structs import DootKey, TaskSpec, TaskName, CodeReference, Location
from doot.actions.base_action import DootBaseAction
from doot.actions.job_injection import JobInjector

class JobGenerate(DootBaseAction):
    """ Run a custom function to generate task specs
      Function is in the form: fn(spec, state) -> list[TaskSpec]
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

    @DootKey.dec.types("from", "inject", "template")
    @DootKey.dec.expands("prefix")
    @DootKey.dec.redirects("update_")
    @DootKey.dec.types("__expansion_count__", hint={"on_fail": 0})
    @DootKey.dec.taskname
    def __call__(self, spec, state, _from, inject, template, prefix, _update, _count, _basename):
        match prefix:
            case "{prefix}":
                prefix = "{JobGenerated}"
            case _:
                pass

        result          = []
        build_queue     = []
        root            = _basename.root()
        base_head       = root.job_head()
        actions, sources = self._prep_base(template)
        match _from:
            case int():
                build_queue += range(_from)
            case str() | pl.Path() | Location():
                build_queue.append(_from)
            case list():
                build_queue += _from
            case None:
                build_queue += [1]
            case _:
                printer.warning("Tried to expand a non-list of args")
                return ActRE.FAIL

        for arg in build_queue:
            _count += 1
            # TODO change job subtask naming scheme
            base_dict = dict(name=root.subtask(prefix, _count),
                             sources=sources,
                             actions = actions or [],
                             required_for=[base_head],
                             )
            match self.build_injection(spec, state, inject, replacement=arg):
                case None:
                    pass
                case dict() as val:
                    base_dict.update(val)

            new_spec  = TaskSpec.build(base_dict)
            result.append(new_spec)

        return { _update : result , "__expansion_count__":  _count }

    def _prep_base(self, base:TaskName|list[ActionSpec]) -> tuple[list, TaskName|None]:
        """
          base can be the literal name of a task (base="group::task") to build off,
          or an indirect key to a list of actions (base_="sub_actions")

          This handles those possibilities and returns a list of actions and maybe a task name

        """
        match base:
            case list():
                assert(all(isinstance(x, (dict, TomlGuard)) for x in base))
                actions  = base
                sources  = [None]
            case TaskName():
                actions = []
                sources = [base]
            case str():
                actions = []
                sources = [TaskName.build(base)]
            case None:
                actions = []
                sources = [None]
            case _:
                raise doot.errors.DootActionError("Unrecognized base type", base)

        return actions, sources

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
            case CodeReference():
                fn = prepfn.try_import()
            case None:
                def fn(x):
                    return x.extra.fpath.suffix

        for x in _onto:
            match fn(x):
                case str() as key if key in mapping:
                    x.ctor = TaskName.build(mapping[key])
                case _:
                    pass
