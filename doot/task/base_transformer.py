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
import types
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import Job_i, Task_i
from doot.enums import TaskMeta_f
from doot.errors import DootDirAbsent
from doot.structs import CodeReference, TaskName, TaskSpec
from doot.task.base_task import DootTask

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@doot.check_protocol
class DootTransformer(DootTask):
    """
      Transformers have an abstract artifact dependency and product,
      and will auto-add to the task graph to transform that artifact
    """
    _help = ["A Basic Task Constructor"]
    _default_flags = TaskMeta_f.TRANSFORMER

    def __init__(self, spec:TaskSpec):
        assert(spec is not None), "Spec is empty"
        super(DootJob, self).__init__(spec)

    @classmethod
    def stub_class(cls, stub) -> TaskStub:
        # Come first
        stub['active_when'].priority    = -90
        stub['required_for'].priority   = -90
        stub['depends_on'].priority     = -100

        return stub

    def stub_instance(self, stub) -> TaskStub:
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
        if bool([x for x in params if not x.invisible]):
            help_lines += ["", "Params:"]
            help_lines += [str(x) for x in cls.param_specs if not x.invisible]

        return "\n".join(help_lines)
