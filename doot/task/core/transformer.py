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
from jgdv import Proto
from jgdv.structs.strang import CodeReference
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.enums import TaskMeta_e
from doot.structs import TaskName
from doot.task.core.core import DootTask

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
    from doot.structs import TaskStub, TaskSpec

##--|
from doot._abstract import Job_i, Task_i
# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@Proto(Task_i)
class DootTransformer(DootTask):
    """
      Transformers have an abstract artifact dependency and product,
      and will auto-add to the task graph to transform that artifact
    """
    _help : ClassVar[tuple[str]] = tuple(["A Basic Task Constructor"])
    _default_flags = TaskMeta_e.TRANSFORMER

    def __init__(self, spec:TaskSpec):
        assert(spec is not None), "Spec is empty"
        super().__init__(spec)

    @classmethod
    def stub_class(cls, stub:TaskStub) -> TaskStub:
        # Come first
        stub['active_when'].priority    = -90
        stub['required_for'].priority   = -90
        stub['depends_on'].priority     = -100

        return stub

    def stub_instance(self, stub:TaskStub) -> TaskStub:
        stub                      = self.__class__.stub_class(stub)
        stub['name'].default      = self.shortname
        if bool(self.doc):
            stub['doc'].default   = [f"\"{x}\"" for x in self.doc]
        return stub

    @classmethod
    def class_help(cls) -> str:
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

        return "\n".join(help_lines)
