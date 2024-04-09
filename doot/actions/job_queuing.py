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


class JobQueueAction(Action_p):
    """
      Queues a list of tasks into the tracker.
      Args are strings converted to simple taskspec's
      `from` is a state list of DootTaskSpec's

      does NOT queue a head task automatically
    """

    @DootKey.kwrap.args
    @DootKey.kwrap.types("from_", hint={"type_":list|DootTaskSpec|None})
    @DootKey.kwrap.redirects_many("from_multi_")
    @DootKey.kwrap.taskname
    def __call__(self, spec, state, _args, _from, _from_multi, _basename):
        subtasks  = []
        subtasks += [DootTaskSpec(_basename.subtask(i), ctor=DootTaskName.build(x), required_for=[_basename.task_head()]) for i,x in enumerate(_args)]

        match _from:
            case [*xs] if all(isinstance(x, DootTaskSpec) for x in xs):
                subtasks += xs
            case DootTaskSpec():
                subtasks.append(_from)
            case None:
                pass
            case _:
                raise doot.errors.DootActionError("Tried to queue a not DootTaskSpec")

        match _from_multi:
            case None:
                pass
            case [*xs]:
                as_keys = [DootKey.build(x) for x in xs]
                for key in as_keys:
                    match key.to_type(spec, state, type_=list|None):
                        case None:
                            pass
                        case DootTaskSpec() as s:
                            subtasks.append(s)
                        case list() as l:
                            subtasks += [spec for spec in l if isinstance(spec, DootTaskSpec)]

        return subtasks

class JobQueueHead(Action_p):
    """ Queue the head/on_completion task of this job"""

    @DootKey.kwrap.types("base")
    @DootKey.kwrap.types("inject")
    @DootKey.kwrap.taskname
    def __call__(self, spec, state, base, inject, _basename):
        head_name       = _basename.task_head()
        head            = []

        match base:
            case str() | DootTaskName():
                head += [DootTaskSpec.build(dict(name=head_name,
                                                     actions=[],
                                                     queue_behaviour="auto")),
                         DootTaskSpec.build(dict(name=head_name.subtask("1"),
                                                     ctor=DootTaskName.build(base),
                                                     depends_on=[head_name],
                                                     extra=inject or {},
                                                     queue_behaviour="auto"))
                    ]
            case list():
                head += [DootTaskSpec.build(dict(name=head_name, actions=base, extra=inject or {}, queue_behaviour="auto"))]
            case None:
                head += [DootTaskSpec.build(dict(name=head_name, queue_behaviour="auto"))]

        return head


class JobChainer(Action_p):
    """
      Add dependencies to task specs, from left to right, by key
      ie: task -> task -> task

      key=[{required_fors}], key2=[{required_fors}]...

      {do="job.chain.->", unpack={literal=[key, key, key], by-name=[taskname, taskname]}},
    """

    @DootKey.kwrap.kwargs
    def __call__(self, spec, state, kwargs):
        for k,v in kwargs.items():
            match DootKey.build(k).to_type(spec, state):
                case list() as l:
                    for x in l:
                        x.required_for += []

                case DootTaskSpec() as s:
                    s.required_for += []
                    pass
