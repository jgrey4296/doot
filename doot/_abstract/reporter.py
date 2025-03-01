#!/usr/bin/env python3
"""
Reporters track events and format them into a report for the user
"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- types
# isort: off
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

    type TraceRecord = Any
# isort: on
# ##-- end types

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

    ##--|
    default  = enum.auto()

##--|

@runtime_checkable
class Reporter_p(Protocol):
    """
      Holds ReportLine_i's, and stores TraceRecords
    """

    @abc.abstractmethod
    def __init__(self, reporters:Maybe[list[ReportLine_p]]=None):
        pass

    @abc.abstractmethod
    def _default_formatter(self, trace:TraceRecord) -> str:
        pass

    @abc.abstractmethod
    def add_trace(self, msg:str, *args:Any, flags:Any=None) -> None:
        pass

##--|

@runtime_checkable
class ReportLine_p(Protocol):
    """
    Reporters, like loggers, are stacked, and each takes the flags and data and maybe runs.
    """

    @abc.abstractmethod
    def __call__(self, trace:TraceRecord) -> Maybe[str]:
        pass

##--|
