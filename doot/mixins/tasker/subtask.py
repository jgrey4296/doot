#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doot.errors import DootDirAbsent, DootTaskError
from doot.structs import DootTaskSpec, DootTaskName, DootCodeReference
from time import sleep

class SubMixin:
    """
    Mixin methods for building subtasks.
    The public method is `build`,
    privately, `_build_subtask` will use `default_task`
    and use the builders `extra.task` value as its ctor if that exists.
    before calling `specialize_subtask` on the built spec
    """
    _default_head_injections = []

    def __init__(self, spec):
        super().__init__(spec)
        self._sub_gen = None
        match self.spec.extra.on_fail((None,), Any).sub_generator():
            case None:
                pass
            case str() as x:
                self._sub_gen = DootCodeReference.from_str(x).try_import()
            case DootCodeReference() as x:
                self._sub_gen = x.try_import()
            case _ as x if callable(x):
                self._sub_gen = x
            case _ as x:
                raise TypeError("Subtask Generator is not a function or nothing", x)



    @abc.abstractmethod
    def _build_subs(self) -> Generator[DootTaskSpec]:
        raise NotImplementedError()

    def build(self, **kwargs) -> Generator:
        head = self._build_head()

        match head:
            case DootTaskSpec(doc=[]):
                head.doc = self.doc
            case DootTaskSpec():
                pass
            case _:
                raise DootTaskError("Failed to build the head task: %s", self.name)

        sub_gen = self._sub_gen(self) if self._sub_gen is not None else self._build_subs()
        for sub in sub_gen:
            match self.specialize_subtask(sub):
                case None:
                    pass
                case DootTaskSpec(name=subname) if not (self.fullname < subname):
                    raise DootTaskError("Subtasks must be part of their parents name: %s : %s", self.name, task.name)
                case DootTaskSpec() as spec_sub:
                    head.depends_on.append(spec_sub.name)
                    yield spec_sub
                case _:
                    raise DootTaskError("Unrecognized subtask generated")

        yield self.specialize_task(head)

    def _build_subtask(self, n:int, uname, **kwargs) -> DootTaskSpec:
        task_spec = self.default_task(uname, extra=kwargs)

        task_ref  = self.spec.extra.on_fail((None,), None|str).sub_task()
        if task_ref is not None:
            task_spec.ctor = DootTaskName.from_str(task_ref)

        return task_spec

    def subtask_name(self, val):
        return self.fullname.subtask(val)

    def specialize_subtask(self, task) -> None|dict|DootTaskSpec:
        return task

    @classmethod
    def stub_class(cls, stub):
        stub['sub_generator'].set(type="callable", default="", prefix="# ", priority= 99, comment="Callable[[TaskObj], Generator[DootTaskSpec]]")
        stub['head_task'].set(priority=100)
        stub['sub_task'].set(type="taskname", default="", prefix="# ", priority=100)
        del stub.parts['actions']
