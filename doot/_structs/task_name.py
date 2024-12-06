#!/usr/bin/env python3
"""

"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
# import abc
import datetime
import enum
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Self, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from pydantic import field_validator, model_validator
from jgdv.structs.strang import Strang
from jgdv.enums.util import FlagsBuilder_m

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

CLEANUP_MARKER : Final[str] = "$cleanup$"

aware_splitter = str

class TaskMeta_f(FlagsBuilder_m, enum.Flag):
    """
      Flags describing properties of a task,
      stored in the Task_i instance itself.
    """

    TASK         = enum.auto()
    JOB          = enum.auto()
    TRANSFORMER  = enum.auto()

    INTERNAL     = enum.auto()
    JOB_HEAD     = enum.auto()
    CONCRETE     = enum.auto()
    DISABLED     = enum.auto()

    EPHEMERAL    = enum.auto()
    IDEMPOTENT   = enum.auto()
    REQ_TEARDOWN = enum.auto()
    REQ_SETUP    = enum.auto()
    IS_TEARDOWN  = enum.auto()
    IS_SETUP     = enum.auto()
    THREAD_SAFE  = enum.auto()
    STATEFUL     = enum.auto()
    STATELESS    = enum.auto()
    VERSIONED    = enum.auto()

    default      = TASK

class _TaskNameOps_m:
    """ Operations Mixin for manipulating TaskNames """

    @classmethod
    def pre_process(cls, data):
        """ Remove 'tasks' as a prefix, and strip quotes  """
        return super().pre_process(data).removeprefix("tasks.").replace('"', "")

    def match_version(self, other) -> bool:
        """ match version constraints of two task names against each other """
        raise NotImplementedError()

class TaskName(_TaskNameOps_m, Strang):
    """
      A Task Name.
      Infers metadata(TaskMeta_f) from the string data it is made of.
      a trailing '+' in the head makes it a job
      a leading '_' in the tail makes it an internal name, eg: group::_.task
      having a '$gen$' makes it a concrete name
      having a '$head$' makes it a job head
      Two separators in a row marks a recall point for root()

      TODO: parameters
    """

    meta                : TaskMeta_f               = TaskMeta_f.default
    args                : dict                    = {}
    version_constraint  : None|str                = None

    _separator          : ClassVar[str]           = doot.constants.patterns.TASK_SEP


    @ftz.cached_property
    def readable(self):
        """ format this name to a readable form
        ie: elide uuids as just <UUID>
        """
        group = self[0:]
        tail = self._subseparator.join([str(x) if not isinstance(x, UUID) else "<UUID>" for x in self.body()])
        return "{}{}{}".format(group, self._separator, tail)
