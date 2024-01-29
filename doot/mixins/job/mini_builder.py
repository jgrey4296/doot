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

from collections import defaultdict
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.structs import DootActionSpec, DootTaskSpec
from doot.mixins.job.subtask import SubMixin

class MiniBuilderMixin(SubMixin):
    """ Instead of using sub_task and head_task references,
    use sub_actions and head_actions to build them.

    """

    def _build_subtask(self, n:int, uname, **kwargs) -> DootTaskSpec:
        actions               = [DootActionSpec.from_data(x) for x in self.spec.extra.on_fail([], list).sub_actions()]
        task                  = super()._build_subtask(n, uname, **kwargs)
        task.actions         += actions
        task.print_levels     = self.spec.print_levels
        return task

    def _build_head(self, **kwargs) -> DootTaskSpec:
        head = super()._build_head(**kwargs)
        spec_head_actions     = [DootActionSpec.from_data(x) for x in self.spec.extra.on_fail([], list).head_actions()]
        head.actions         += spec_head_actions

        return head

    @classmethod
    def stub_class(cls, stub):
        if 'sub_task' in stub.parts:
            del stub.parts['sub_task']

        if 'head_task' in stub.parts:
            del stub.parts['head_task']

        stub['sub_actions'].set(type="list[dict]",   default=[])
        stub['head_actions'].set(type="list[dict]", default=[])



class HeadOnlyJobMixin(SubMixin):
    """
      doesn't build subtasks, instead collects the specified 'head_inject' kwargs and passes them to the head task

    """

    def build(self, **kwargs) -> Generator:
        inject_keys = self.spec.extra.on_fail([]).head_inject()
        inject_dict = defaultdict(list, {x:[] for x in inject_keys})

        sub_gen = self._sub_gen(self) if self._sub_gen is not None else self._build_subs()
        for sub in sub_gen:
            match self.specialize_subtask(sub):
                case None:
                    pass
                case DootTaskSpec() as spec_sub:
                    for x in inject_keys:
                        inject_dict[x].append(spec_sub.extra[x])
                case _:
                    raise DootTaskError("Unrecognized subtask generated")

        head = self._build_head(**inject_dict)

        match head:
            case DootTaskSpec(doc=[]):
                head.doc = self.doc
            case DootTaskSpec():
                pass
            case _:
                raise DootTaskError("Failed to build the head task: %s", self.name)

        yield self.specialize_task(head)


    @classmethod
    def stub_class(cls, stub):
        stub['head_inject'].set(type="list[str]", default=[])
