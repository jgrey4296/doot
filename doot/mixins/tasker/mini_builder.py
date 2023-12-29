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


class MiniBuilderMixin:

    def specialize_subtask(self, task) -> DootTaskSpec:
        task.actions         = [DootActionSpec.from_data(x) for x in self.spec.extra.sub_actions]
        task.print_levels    = self.spec.print_levels
        return task


    def _build_head(self, **kwargs) -> DootTaskSpec:
        head = self.default_task(None, TomlGuard(kwargs))
        spec_head_actions = [DootActionSpec.from_data(x) for x in self.spec.extra.on_fail([], list).head_actions()]
        head.actions = spec_head_actions
        head.queue_behaviour = "auto"

        return head

    @classmethod
    def stub_class(cls, stub):
        stub.ctor                  = cls
        if 'sub_task' in stub.parts:
            del stub.parts['sub_task']

        if 'head_task' in stub.parts:
            del stub.parts['head_task']

        stub['sub_actions'].default  = list()
        stub['head_actions'].default = list()
        return stub
