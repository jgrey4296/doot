#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
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
import more_itertools as mitz
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import Action_p
from doot.structs import CodeReference, DKey, TaskName, TaskSpec, DKeyed

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

class JobQueueAction(Action_p):
    """
      Queues a list of tasks/specs into the tracker.

      1) Queue Named Tasks: {do='job.queue', args=['group::task'] }
      2) Queue Expanded TaskSpecs: {do='job.queue', from_='state_key' }


      tasks can be specified by name in `args`
      and from prior expansion state vars with `from_` (accepts a list)

      `after` can be used to specify additional `depends_on` entries.
      (the job head is specified using `$head$`)
    """

    @DKeyed.args
    @DKeyed.redirects("from_", multi=True)
    @DKeyed.types("after", check=list|TaskName|str|None, fallback=None)
    @DKeyed.taskname
    def __call__(self, spec, state, _args, _from, _after, _basename) -> list:
        subtasks               = []
        queue : list[TaskSpec] = []
        _after                     = self._expand_afters(_after, _basename)

        if _args:
            queue += self._build_args(_basename, _args)

        if _from:
            queue += self._build_from_list(_basename, _from, spec,state)

        for sub in queue:
            match sub:
                case TaskSpec():
                    sub.depends_on += _after
                    subtasks.append(sub)
                case x:
                    raise doot.errors.DootActionError("Tried to queue a not TaskSpec", x)

        return subtasks

    def _expand_afters(self, afters:list|str|None, base:TaskName) -> list[TaskName]:
        result = []
        match afters:
            case str():
                afters = [afters]
            case None:
                afters = []

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

    def _build_from_list(self, base:TaskName, froms:list[DKey], spec, state) -> list:
        result  = []
        root    = base.root()
        head    = base.job_head()
        assert(all(isinstance(x, DKey) for x in froms))

        for key in froms:
            if key == "from_":
                continue
            match key.expand(spec, state):
                case None:
                    pass
                case list() as l:
                    result += l
                case TaskSpec() as s:
                    result.append(s)

        return result

    def _build_from(self, base, _from:list) -> list:
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

    @DKeyed.types("base")
    @DKeyed.types("inject")
    @DKeyed.taskname
    def __call__(self, spec, state, base, inject, _basename):
        raise DeprecationWarning("This Is No Longer needed")
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

    @DKeyed.kwargs
    def __call__(self, spec, state, kwargs):
        for k,v in kwargs.items():
            match DKey(k).expand(spec, state):
                case list() as l:
                    for x in l:
                        x.required_for += []

                case TaskSpec() as s:
                    s.required_for += []
                    pass
