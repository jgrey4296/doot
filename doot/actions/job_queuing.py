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
from doot._abstract import Action_p
from doot.structs import DootKey, TaskSpec, TaskName, CodeReference

class JobQueueAction(Action_p):
    """
      Queues a list of tasks into the tracker.

      1) Queue Named Tasks: {do='job.queue', args=['group::task'] }
      2) Queue Expanded TaskSpecs: {do='job.queue', from_="state_key" }
    """

    @DootKey.dec.args
    @DootKey.dec.types("from_", hint={"type_":list|TaskSpec|None})
    @DootKey.dec.redirects_many("from_multi_")
    @DootKey.dec.types("after", hint={"type_":list|TaskName|str|None, "on_fail":None})
    @DootKey.dec.taskname
    def __call__(self, spec, state, _args, _from, _from_multi, _after, _basename) -> list:
        # TODO maybe expand args
        subtasks               = []
        queue : list[TaskSpec] = []
        _after                     = self._expand_afters(_after, _basename)

        if _args:
            queue += self._build_args(_basename, _args)

        if _from:
            queue += self._build_from(_basename, _from)

        if _from_multi:
            queue += self._build_from_multi(_basename, _from_multi, spec, state)

        for sub in queue:
            match sub:
                case TaskSpec():
                    sub.depends_on += _after
                    subtasks.append(sub)
                case x:
                    raise doot.errors.DootActionError("Tried to queue a not TaskSpec", x)

        return subtasks

    def _expand_afters(self, afters, base):
        result = []
        match afters:
            case None:
                return []
            case "$head$":
                return [base.head_task()]
            case str():
                return [TaskName.build(afters)]
            case list():
                for x in afters:
                    if x == "$head$":
                        result.append(base.head_task())
                    else:
                        result.append(TaskName.build(x))

        return result



    def _build_args(self, base, args) -> list:
        result = []
        root   = base.root()
        head   = base.job_head()
        for i,x in enumerate(args):
            sub = TaskSpec.build(dict(
                name=root.subtask(i),
                sources=[TaskName.build(x)],
                required_for=[head],
                depends_on=[],
                ))
            result.append(sub)

        return result

    def _build_from_multi(self, base:TaskName, froms:list[DootKey], spec, state) -> list:
        result  = []
        root    = base.root()
        head    = base.job_head()
        assert(all(isinstance(x, DootKey) for x in froms))

        for key in froms:
            match key.to_type(spec, state, type_=list|TaskSpec|None):
                case None:
                    pass
                case list() as l:
                    result += l
                case TaskSpec() as s:
                    result.append(s)

        return result

    def _build_from(self, base, _from) -> list:
        result = []
        head = base.job_head()
        match _from:
            case None:
                pass
            case list() as l:
                result += l

        return result

class JobQueueHead(Action_p):
    """ Queue the head/on_completion task of this job"""

    @DootKey.dec.types("base")
    @DootKey.dec.types("inject")
    @DootKey.dec.taskname
    def __call__(self, spec, state, base, inject, _basename):
        root            = _basename.root()
        head_name       = _basename.job_head()
        head            = []

        match base:
            case str() | TaskName():
                head += [TaskSpec.build(dict(name=head_name,
                                                 actions=[],
                                                 queue_behaviour="auto")),
                         TaskSpec.build(dict(name=root.job_head().subtask("1"),
                                                 sources=[TaskName.build(base)],
                                                 depends_on=[head_name],
                                                 extra=inject or {},
                                                 queue_behaviour="auto"))
                    ]
            case list():
                head += [TaskSpec.build(dict(name=head_name, actions=base, extra=inject or {}, queue_behaviour="auto"))]
            case None:
                head += [TaskSpec.build(dict(name=head_name, queue_behaviour="auto"))]

        return head

class JobChainer(Action_p):
    """
      Add dependencies to task specs, from left to right, by key
      ie: task -> task -> task

      key=[{required_fors}], key2=[{required_fors}]...

      {do="job.chain.->", unpack={literal=[key, key, key], by-name=[taskname, taskname]}},
    """

    @DootKey.dec.kwargs
    def __call__(self, spec, state, kwargs):
        for k,v in kwargs.items():
            match DootKey.build(k).to_type(spec, state):
                case list() as l:
                    for x in l:
                        x.required_for += []

                case TaskSpec() as s:
                    s.required_for += []
                    pass
