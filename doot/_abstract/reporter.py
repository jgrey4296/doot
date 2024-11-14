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

class Report_f(enum.Flag):
    """ Flags to mark what a reporter reports
      For categorizing the most common parts of Reporting.
    """
    INIT     = enum.auto()
    SUCCEED  = enum.auto()
    FAIL     = enum.auto()
    EXECUTE  = enum.auto()
    SKIP     = enum.auto()

    STALE    = enum.auto()
    CLEANUP  = enum.auto()

    STATUS   = enum.auto()

    PLUGIN   = enum.auto()
    TASK     = enum.auto()
    JOB      = enum.auto()
    ACTION   = enum.auto()
    CONFIG   = enum.auto()
    ARTIFACT = enum.auto()

    OTHER    = enum.auto()
    #

    default  = enum.auto()

class Reporter_p(abc.ABC):
    """
      Holds ReportLine_i's, and stores TraceRecords
    """

    @abc.abstractmethod
    def __init__(self, reporters:list[ReportLine_p]=None):
        pass

    @abc.abstractmethod
    def _default_formatter(self, trace:"TraceRecord") -> str:
        pass

    @abc.abstractmethod
    def add_trace(self, msg, *args, flags=None):
        pass

class ReportLine_p(abc.ABC):
    """
    Reporters, like loggers, are stacked, and each takes the flags and data and maybe runs.
    """

    @abc.abstractmethod
    def __call__(self, trace:"TraceRecord") -> None|str:
        pass
