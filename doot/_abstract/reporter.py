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
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from tomlguard import TomlGuard
from doot.enums import ReportEnum
from doot.structs import DootTraceRecord

class Reporter_i:
    """
      Holds ReportLine_i's, and stores DootTraceRecords
    """

    def __init__(self, reporters:list[ReportLine_i]=None):
        self._full_trace     : list[DootTraceRecord]       = []
        self._reporters      : list[ReportLine_i] = list(reporters or [self._default_formatter])

    def _default_formatter(self, trace:DootTraceRecord) -> str:
        return str(trace)

    def __str__(self):
        raise NotImplementedError()

    def trace(self, msg, *args, flags=None):
        self._full_trace.append(DootTraceRecord(msg, flags, args))


class ReportLine_i:
    """
    Reporters, like loggers, are stacked, and each takes the flags and data and maybe runs.
    """

    def __call__(self, trace:DootTraceRecord) -> None|str:
        raise NotImplementedError(self.__class__, "call")
