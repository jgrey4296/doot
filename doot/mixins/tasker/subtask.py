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
from doot.structs import DootStructuredName, DootTaskSpec
from time import sleep

class SubMixin:
    """
    Mixin methods for building subtasks.
    The public method is `build`,
    privately, `_build_subtask` will use `default_task`
    and use the builders `extra.task` value as its ctor if that exists.
    before calling `specialize_subtask` on the built spec
    """

    @abc.abstractmethod
    def _build_subs(self) -> Generator[DootTaskSpec]:
        raise NotImplementedError()

    @abc.abstractmethod
    def build(self, **kwargs) -> Generator:
        raise NotImplementedError()

    def _sleep_subtask(self):
        if self.sleep_notify:
            logging.info("Sleep Subtask")
        sleep(self.sleep_subtask)

    def _build_subtask(self, n:int, uname, **kwargs) -> DootTaskSpec:
        task_spec = self.default_task(uname, extra=kwargs)

        task_ref = self.spec.extra.on_fail((None,), None|str).sub_task()
        if task_ref is not None:
            task_spec.ctor_name = DootStructuredName.from_str(task_ref)

        task      = self.specialize_subtask(task_spec)
        if task is None:
            return

        if not (self.fullname < task.name):
            raise DootTaskError("Subtasks must be part of their parents name: %s : %s", self.name, task.name)

        return task

    def subtask_name(self, val):
        return self.fullname.subtask(val)

    def specialize_subtask(self, task) -> None|dict|DootTaskSpec:
        return task


    @classmethod
    def stub_class(cls, stub):
        stub['sub_task'].type = "task_iden"
        stub['sub_task'].default = ""
        stub['sub_task'].prefix = "# "
        del stub.parts['actions']
