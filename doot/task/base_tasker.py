#!/usr/bin/env python3
"""
Utility classes for building tasks with a bit of structure
"""
##-- imports
from __future__ import annotations

# import abc
# import datetime
# import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
# from uuid import UUID, uuid1
# from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from tomlguard import TomlGuard
import doot
import doot.errors
from doot.constants import SUBTASKED_HEAD
from doot.enums import TaskFlags
from doot.structs import DootTaskSpec, TaskStub, TaskStubPart, DootStructuredName
from doot._abstract import Tasker_i, Task_i
from doot.mixins.importer import ImporterMixin
from doot.errors import DootDirAbsent

@doot.check_protocol
class DootTasker(Tasker_i, ImporterMixin):
    """ Util Class for building single tasks
      wraps with setup and teardown tasks,
      manages cleaning,
      and holds state

    """
    _help = ["A Basic Task Constructor"]
    _default_flags = TaskFlags.TASKER

    def __init__(self, spec:DootTaskSpec):
        assert(spec is not None), "Spec is empty"
        super(DootTasker, self).__init__(spec)

    def default_task(self, name:str|DootStructuredName|None, extra:None|dict|TomlGuard) -> DootTaskSpec:
        task_name = None
        match name:
            case None:
                task_name = self.fullname.subtask(SUBTASKED_HEAD)
            case str():
                task_name = self.fullname.subtask(name)
            case DootStructuredName():
                task_name = name
            case _:
                raise doot.errors.DootTaskError("Bad value used to make a subtask in %s : %s", self.name, name)

        assert(task_name is not None)
        return DootTaskSpec(name=task_name, extra=TomlGuard(extra))

    def is_stale(self, task:Task_i):
        return False

    def build(self, **kwargs) -> Generator[DootTaskSpec]:
        logging.debug("-- tasker %s expanding tasks", self.name)
        if bool(kwargs):
            logging.debug("received kwargs: %s", kwargs)
            self.args.update(kwargs)

        yield self._build_head()

    def specialize_task(self, task):
        return task

    @classmethod
    def stub_class(cls, stub) -> TaskStub:
        stub.ctor                 = cls
        stub['version'].default   = cls._version
        stub['doc'].default       = [f"\"{x}\"" for x  in cls.class_help().split("\n")]
        stub['flags'].default     = cls._default_flags
        stub['flags'].prefix      = "# "
        stub['head_task'].type    = "task_iden"
        stub['head_task'].default = ""
        stub['head_task'].prefix  = "# "
        return stub

    def stub_instance(self, stub) -> TaskStub:
        stub                      = self.__class__.stub_class(stub)
        stub['name'].default      = self.fullname
        if bool(self.doc):
            stub['doc'].default   = [f"\"{x}\"" for x in self.doc]
        stub['flags'].default     = self.spec.flags
        return stub

    def _build_head(self, **kwargs) -> DootTaskSpec:
        logging.debug("Building Head Task for: %s", self.name)
        task_spec                             = self.default_task(None, TomlGuard(kwargs))

        task_ref = self.spec.extra.on_fail((None,), None|str).head_task()
        if task_ref is not None:
            task_spec.ctor_name = DootStructuredName.from_str(task_ref)

        maybe_task : DootTaskSpec | None = self.specialize_task(task_spec)

        match maybe_task:
            case None:
                raise DootTaskError("Task Failed to specialize the head task: %s", self.name)
            case _ if not bool(maybe_task.doc):
                maybe_task.doc = self.doc
                return maybe_task
            case _:
                return maybe_task
