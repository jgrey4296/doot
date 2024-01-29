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
from doot.structs import DootTaskSpec, TaskStub, TaskStubPart, DootTaskName, DootCodeReference, DootStructuredName
from doot._abstract import Job_i, Task_i
from doot.mixins.importer import ImporterMixin
from doot.errors import DootDirAbsent

@doot.check_protocol
class DootJob(Job_i, ImporterMixin):
    """ Util Class for building single tasks
      wraps with setup and teardown tasks,
      manages cleaning,
      and holds state

    """
    _help = ["A Basic Task Constructor"]
    _default_flags = TaskFlags.JOB

    def __init__(self, spec:DootTaskSpec):
        assert(spec is not None), "Spec is empty"
        super(DootJob, self).__init__(spec)

    def default_task(self, name:str|DootTaskName|None, extra:None|dict|TomlGuard) -> DootTaskSpec:
        task_name = None
        match name:
            case None:
                task_name = self.fullname.subtask(SUBTASKED_HEAD)
            case str():
                task_name = self.fullname.subtask(name)
            case DootTaskName():
                task_name = name
            case _:
                raise doot.errors.DootTaskError("Bad value used to make a subtask in %s : %s", self.name, name)

        assert(task_name is not None)
        return DootTaskSpec(name=task_name, extra=TomlGuard(extra))

    def is_stale(self, task:Task_i):
        return False

    def build(self, **kwargs) -> Generator[DootTaskSpec]:
        logging.debug("-- job %s expanding tasks", self.name)
        if bool(kwargs):
            logging.debug("received kwargs: %s", kwargs)
            self.args.update(kwargs)

        head = self._build_head()
        yield self.specialize_task(head)

    def specialize_task(self, task):
        return task

    @classmethod
    def stub_class(cls, stub) -> TaskStub:
        # Come first
        stub['active_when'].priority    = -90
        stub['required_for'].priority   = -90
        stub['depends_on'].priority     = -100

        stub['head_task'].set(type="taskname", default="", prefix="# ", priority=100)
        stub['queue_behaviour'].default = "default"
        stub['queue_behaviour'].comment = "default | auto | reactive"
        return stub

    def stub_instance(self, stub) -> TaskStub:
        stub                      = self.__class__.stub_class(stub)
        stub['name'].default      = self.fullname
        if bool(self.doc):
            stub['doc'].default   = [f"\"{x}\"" for x in self.doc]
        return stub

    def _build_head(self, **kwargs) -> None|DootTaskSpec:
        logging.debug("Building Head Task for: %s", self.name)
        inject_keys = set(self.spec.inject)
        inject_dict = {k: self.spec.extra[k] for k in inject_keys}
        extra       = {}
        extra.update(kwargs)
        extra.update(inject_dict)
        task_spec                 = self.default_task(None, TomlGuard(extra))
        task_spec.queue_behaviour = "auto"
        task_spec.print_levels    = self.spec.print_levels

        task_ref                  = self.spec.extra.on_fail((None,), None|str).head_task()
        if task_ref is not None:
            task_spec.ctor = DootStructuredName.build(task_ref)

        return task_spec
