#!/usr/bin/env python3
"""

"""
# ruff: noqa:

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
import collections
import contextlib
import hashlib
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref
import atexit # for @atexit.register
import faulthandler
# ##-- end stdlib imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe, DateTime
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from doot.workflow._interface import TaskName_p
    type Logger = logmod.Logger
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
SEGMENT_SIZES  : Final[tuple[int,int,int]]  = (1, 3, 1)
GAP            : Final[str]                 = " "*SEGMENT_SIZES[1]
##-- segment dicts
TRACE_LINES_ASCII     : Final[dict[str, str|tuple]] = {
    "root"            : "T",
    "wait"            : "|",
    "branch"          : ("|", "->=", "["),
    "act"             : ("|", "",  "::"),
    "inactive"        : ":",
    "begin"           : ("|", "...", "Y"),
    "return"          : ("",  "=",   "<]"),
    "pause"           : ("",  "-", "<]"),
    "resume"          : ("|", "->-", "["),
    "result"          : ("|", "<<<", "]"),
    "fail"            : ("|", "...", "X:"),
    "finished"        : "⟘",
    "gap"             : (" "*SEGMENT_SIZES[1]),
    "just_char"       : " ",
}

##-- end segment dicts

# eg: {┣─}{╮}
LINE_PASS_FMT            : Final[str] = "{ctx}{act}"
# eg: {┊ ┊ }{┃} [{blah}] : {bloo}
LINE_MSG_FMT             : Final[str] = "{ctx}{act}{gap}[{info}]{gap2}: {detail}"
TIME_FMT                 : Final[str] = "%H:%M"

ACT_SPACING              : Final[int] = 4
MSG_SPACING              : Final[int] = 6
# Body:

class TraceRecord_d:
    """ For Storing what happened, where, and why """

    __slots__ = ("what", "when", "where", "why")

    def __init__(self, *, what:str, where:str, why:str, when:DateTime) -> None:
        self.what   = what
        self.where  = where
        self.why    = why
        self.when   = when

class ReportStackEntry_d:
    """ Data for storing the context of the reporter """
    __slots__ = ("data", "depth", "extra", "log_extra", "log_level", "prefix", "state")
    log_extra  : dict
    log_level  : int
    depth      : int
    state      : str
    data       : dict
    prefix     : list[str]
    extra      : dict

    def __init__(self, **kwargs:Any) -> None:
        # Required args:
        self.log_extra = kwargs.pop("log_extra")
        self.log_level = kwargs.pop("log_level")
        self.state     = kwargs.pop("state")
        self.data      = kwargs.pop("data")
        # Optional Args:
        self.prefix    = kwargs.pop("prefix", [])
        self.depth     = kwargs.pop("depth", 1)
        self.extra     = dict(kwargs)

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.depth}): level:{self.log_level}>"

# Sub Protocols

##--|

@runtime_checkable
class ReportGroup_p(Protocol):

    def _out(self, key:str, *, info:Maybe=None, msg:Maybe=None, level:int=0) -> None: ...

class WorkflowGroup_p(ReportGroup_p, Protocol):
    """
    A Re-entrant ctx manager,
    used for reporting user-level information about a
    task workflow run.

    """

    def root(self) -> Self: ...

    def wait(self) -> Self: ...

    def act(self, info:str, msg:str) -> Self: ...

    def fail(self, *, info:Maybe[str]=None, msg:Maybe[str]=None) -> Self: ...

    def branch(self, name:str|TaskName_p, info:Maybe[str]=None) -> Self: ...

    def pause (self, reason:str) -> Self: ...

    def result(self, state:list[str], info:Maybe[str]=None) -> Self: ...

    def resume(self, name:str|TaskName_p) -> Self: ...

    def finished(self) -> Self: ...

    def queue(self, num:int) -> Self: ...

    def state_result(self, *vals:str) -> Self: ...

    def line(self, msg:Maybe[str]=None, char:Maybe[str]=None) -> Self: ...

class GeneralGroup_p(ReportGroup_p, Protocol):
    """ Reporter Methods for general user facing messages """

    def header(self) -> Self: ...

    def user(self, msg:str, *rest:Any, **kwargs:Any) -> Self: ...

    def trace(self, msg:str, *rest:Any, **kwargs:Any) -> Self: ...

    def failure(self, msg:str, *rest:Any, **kwargs:Any) -> Self: ...

    def detail(self, msg:str, *rest:Any, **kwargs:Any) -> Self: ...

    def warn(self, msg:str, *rest:Any, **kwargs:Any) -> Self: ...

    def error(self, msg:str, *rest:Any, **kwargs:Any) -> Self: ...
    ##--|

    def line(self, msg:Maybe[str]=None, char:Maybe[str]=None) -> Self: ...

    def gap(self) -> Self: ...

# Main Protocols

class TreeGroup_p(ReportGroup_p, Protocol):
    pass

class SummaryGroup_p(ReportGroup_p, Protocol):

    def start(self) -> None: ...

    def finish(self) -> None: ...

    def add(self, key:str, *vals:Any) -> Self: ...

    def summarise(self) -> Self: ...

    pass
##--|

@runtime_checkable
class Reporter_p(Protocol):
    """
    Reporters provide attr access to any registered ReportGroup_p's,
    for formatted printing of workflow information
    """
    _entry_count  : int
    _fmt          : ReportFormatter_p
    _logger       : Logger
    _stack        : list[ReportStackEntry_d]

    @property
    def state(self) -> ReportStackEntry_d: ...

    @property
    def wf(self) -> WorkflowGroup_p: ...

    @property
    def gen(self) -> GeneralGroup_p: ...

    @property
    def tree(self) -> TreeGroup_p: ...

    @property
    def summary(self) -> SummaryGroup_p: ...

    ##--|

    def __enter__(self) -> Self: ...

    def __exit__(self, *exc:Any) -> bool: ...

    def push_state(self, state:str, **kwargs:Any) -> Self: ...

    def pop_state(self) -> Self: ...

    def active_level(self, level:int) -> None: ...

@runtime_checkable
class ReportFormatter_p(Protocol):

    def __call__(self, key:str, *, info:Maybe[str]=None, msg:Maybe[str]=None, ctx:Maybe[list]=None) -> str: ...

    def get_segment(self, key:str) -> Maybe[str]: ...
