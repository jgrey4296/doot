#!/usr/bin/env python3
"""
Utility classes for building tasks with a bit of structure
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
import re
import time
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto, Mixin
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.strang import CodeReference
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import Job_p, Task_p
from doot.enums import TaskMeta_e
from doot.structs import TaskName, TaskSpec
from doot.task.core.task import DootTask

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from doot.structs import TaskStub

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

SUBTASKED_HEAD = doot.constants.patterns.SUBTASKED_HEAD

class _JobStubbing_m:
    @classmethod
    def stub_class(cls, stub:TaskStub) -> TaskStub:
        # Come first
        stub['active_when'].priority    = -90
        stub['required_for'].priority   = -90
        stub['depends_on'].priority     = -100

        stub['head_task'].set(type="taskname", default="", prefix="# ", priority=100)
        stub['queue_behaviour'].default = "default"
        stub['queue_behaviour'].comment = "default | auto | reactive"
        return stub

    def stub_instance(self, stub:TaskStub) -> TaskStub:
        stub                      = self.__class__.stub_class(stub)
        stub['name'].default      = self.shortname
        if bool(self.doc):
            stub['doc'].default   = [f"\"{x}\"" for x in self.doc]
        return stub



@Proto(Job_p, check=False)
@Mixin(_JobStubbing_m)
class DootJob(DootTask):
    """ Util Class for building single tasks
      wraps with setup and teardown tasks,
      manages cleaning,
      and holds state

    """
    _help : ClassVar[tuple[str]] = tuple(["A Basic Task Constructor"])
    _default_flags = TaskMeta_e.JOB

    def __init__(self, spec:TaskSpec):
        assert(spec is not None), "Spec is empty"
        super().__init__(spec)

    def default_task(self, name:Maybe[str|TaskName], extra:Maybe[dict|ChainGuard]) -> TaskSpec:
        task_name = None
        match name:
            case None:
                task_name = self.name.push(SUBTASKED_HEAD)
            case str():
                task_name = self.name.push(name)
            case TaskName():
                task_name = name
            case _:
                raise doot.errors.StructError("Bad value used to make a subtask in %s : %s", self.shortname, name)

        assert(task_name is not None)
        return TaskSpec(name=task_name, extra=ChainGuard(extra))

    def is_stale(self, task:Task_p) -> bool:
        return False

    def specialize_task(self, task:Task_p) -> Task_p:
        return task

    def expand_job(self) -> list:
        return []

    @classmethod
    def class_help(cls) -> list[str]:
        """ Job *class* help. """
        help_lines = [f"Job : {cls.__qualname__} v{cls._version}    ({cls.__module__}:{cls.__qualname__})", ""]

        mro = " -> ".join(x.__name__ for x in cls.mro())
        help_lines.append(f"Job MRO: {mro}")
        help_lines.append("")
        help_lines += cls._help

        params = cls.param_specs
        if bool(params):
            help_lines += ["", "Params:"]
            help_lines += [y for x in cls.param_specs if (y:=str(x))]

        return help_lines
