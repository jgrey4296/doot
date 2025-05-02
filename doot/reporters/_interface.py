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
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    type Logger = logmod.Logger
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
SEGMENT_SIZES : Final[tuple[int,int,int]] = (1, 3, 1)
GAP      : Final[str] = " "*SEGMENT_SIZES[1]
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

class ReportStackEntry_d:
    log_extra : dict
    log_level : int
    depth     : int
    state     : str
    data      : dict
    prefix    : list[str]

    def __init__(self, **kwargs:Any) -> None:
        self.log_extra = kwargs.pop("log_extra")
        self.log_level = kwargs.pop("log_level")
        self.state     = kwargs.pop("state")
        self.data      = kwargs.pop("data")
        self.prefix    = kwargs.pop("prefix", [])
        self.depth     = kwargs.pop("depth", 1)
        self.extra     = dict(kwargs)


class Reporter_d:
    _act_trace      : list
    _fmt            : TraceFormatter_p
    _stack          : list[ReportStackEntry_d]
    _entry_count    : int
    _logger         : Logger
    _log_level      : int

@runtime_checkable
class WorkflowReporter_p(Protocol):
    """
    A Re-entrant ctx manager,
    used for reporting user-level information about a
    task workflow run.

    """

    def __enter__(self) -> Self:
        # calls branch|resume
        # level+
        pass

    def __exit__(self, *exc:Any) -> bool:
        # pause|result|fail|return
        # level-
        pass

    def root(self) -> Self:
        # pass fmt
        pass

    def wait(self) -> Self:
        # pass fmt
        pass

    def act(self, info:str, msg:str) -> Self:
        # msg fmt
        pass

    def fail(self, *, info:Maybe[str]=None, msg:Maybe[str]=None) -> Self:
        # msg fmt
        pass

    def branch(self, name:str) -> Self:
        # pass fmt
        pass

    def pause (self, reason:str) -> Self:
        # msg fmt
        pass

    def result(self, state:list[str]) -> Self:
        # Maybe msg fmt
        pass

    def resume(self, name:str) -> Self:
        # msg fmt
        pass

    def finished(self) -> Self:
        # pass fmt
        pass

    def queue(self, num:int) -> Self:
        raise NotImplementedError()

    def state_result(self, *vals:str) -> Self:
        raise NotImplementedError()

@runtime_checkable
class GeneralReporter_p(Protocol):
    """ Reporter Methods for general user facing messages """

    def header(self) -> Self:
        pass

    def summary(self) -> Self:
        pass

    def trace(self, msg:str, *rest:str) -> Self:
        pass

    def failure(self, msg:str, *rest:str) -> Self:
        pass

    def warn(self, msg:str, *rest:str) -> Self:
        pass

@runtime_checkable
class Reporter_p(WorkflowReporter_p, GeneralReporter_p, Protocol):
    @property
    def state(self) -> ReportStackEntry_d:
        pass

    def add_trace(self, msg:str, *args:Any, flags:Any=None) -> None:
        pass

    def push_state(self, state:str, **kwargs:Any) -> Self:
        pass

    def pop_state(self) -> Self:
        pass
@runtime_checkable
class TraceFormatter_p(Protocol):

    def __call__(self, key:str, *, info:Maybe[str]=None, msg:Maybe[str]=None, ctx:Maybe[list]=None) -> str:
        pass


    def get_segment(self, key:str) -> Maybe[str]:
        pass
