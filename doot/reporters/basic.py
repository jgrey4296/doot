#!/usr/bin/env python3
"""
The Basic implementation of a reporter.

_WorkflowReporter_m implements WorkflowReporter_p methods,
while _GenReporter_m implements GeneralReporter_p methods.



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
import sys
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref
import atexit # for @atexit.register
import faulthandler
# ##-- end stdlib imports

from jgdv import Proto, Mixin
import doot
from . import _interface as API  # noqa: N812
from .formatter import TraceFormatter

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
logging.setLevel(logmod.WARN)
##-- end logging

# Vars:
LINE_LEN   : Final[int] = 46
LINE_CHAR  : Final[str] = "-"
INIT_LEVEL : Final[int] = logmod.WARN
# Body:

class _WorkflowReporter_m:

    _out : Callable

    def root(self) -> Self:
        self._out("root", level=5)
        return self

    def wait(self) -> Self:
        self._out("wait")
        return self

    def act(self, info:str, msg:str, level:int=0) -> Self:
        self._out("act", info=info, msg=msg, level=level)
        return self

    def fail(self, *, info:Maybe[str]=None, msg:Maybe[str]=None) -> Self:
        self._out("fail", info=info, msg=msg, level=40)
        return self

    def branch(self, name:str, info:Maybe[str]=None) -> Self:
        self._out("branch", level=5)
        self._out("begin", info=info or "Start", msg=name, level=5)
        return self

    def pause (self, reason:str) -> Self:
        self._out("pause", msg=reason, level=5)
        return self

    def result(self, state:list[str], info:Maybe[str]=None) -> Self:
        self._out("result" , msg=",".join(str(x) for x in state), info=info, level=5)
        return self

    def resume(self, name:str) -> Self:
        self._out("resume", msg=name, level=5)
        return self

    def finished(self) -> Self:
        self._out("finished", level=5)
        return self

    def queue(self, num:int) -> Self:
        raise NotImplementedError()

    def state_result(self, *vals:str) -> Self:
        raise NotImplementedError()

class _GenReporter_m:
    log           : Logger
    active_level  : Callable
    _curr         : API.ReportStackEntry_d

    def gap(self) -> Self:
        self.log.info("")
        return self

    def line(self, msg:Maybe[str]=None, char:Maybe[str]=None) -> Self:
        char = char or LINE_CHAR
        match msg:
            case str() as x:
                val = x.strip()
                val = val.center(len(val) + 4, " ")
                val = val.center(LINE_LEN, char)
                self.log.info(val, extra=self._curr.log_extra)
            case _:
                self.log.info(char*LINE_LEN, extra=self._curr.log_extra)

        return self

    def header(self) -> Self:
        self.active_level(logmod.INFO)
        self._curr.log_extra['colour'] = "green"
        self.line()
        self.line("Doot")
        self.line()
        return self

    def summary(self) -> Self:
        self.active_level(logmod.WARN)
        match self._curr.state:
            case "fail":
                self._curr.log_extra['colour'] = "red"
                msg = doot.config.on_fail("Errored").shutdown.notify.fail_msg()
            case _:
                msg = doot.config.on_fail("Success").shutdown.notify.success_msg()

        self.line(msg)
        # TODO the report
        self.gap()
        return self

    def user(self, msg:str, *rest:str, **kwargs:str) -> Self:  # noqa: ARG002
        self.log.warning(msg, *rest)
        return self

    def trace(self, msg:str, *rest:str, **kwargs:str) -> Self:  # noqa: ARG002
        self.log.info(msg, *rest)
        return self

    def detail(self, msg:str, *rest:str, **kwargs:str) -> Self:  # noqa: ARG002
        self.log.debug(msg, *rest)
        return self

    def failure(self, msg:str, *rest:str, **kwargs:str) -> Self:  # noqa: ARG002
        match doot.is_setup:
            case False:
                print(msg % rest, file=sys.stderr)
            case _:
                self.log.exception(msg, *rest)

        return self

    def warn(self, msg:str, *rest:str, **kwargs:str) -> Self:  # noqa: ARG002
        match doot.is_setup:
            case False:
                print(msg % rest, file=sys.stderr)
            case _:
                self.log.warn(msg, *rest)

        return self

    def error(self, msg:str, *rest:str, **kwargs:str) -> Self:  # noqa: ARG002
        match doot.is_setup:
            case False:
                print(msg % rest, file=sys.stderr)
            case _:
                self.log.error(msg, *rest)

        return self

##--|

@Proto(API.WorkflowReporter_p, API.GeneralReporter_p)
@Mixin(_GenReporter_m, _WorkflowReporter_m)
class BasicReporter(API.Reporter_d):
    """ The initial reporter for prior to configuration """

    def __init__(self, *args:Any, logger:Maybe[Logger]=None, segments:Maybe[dict]=None, **kwargs:Any) -> None:
        super().__init__(*args, **kwargs)
        self._logger            = logger
        self._fmt               = TraceFormatter(segments=segments or API.TRACE_LINES_ASCII)
        self._stack             = []
        self._entry_count       = 0
        self.ctx                = []
        self._act_trace         = []

        initial_entry           = API.ReportStackEntry_d(state="initial",
                                                         data={},
                                                         log_extra={"colour":"blue"},
                                                         log_level=INIT_LEVEL,
                                                         )
        self._stack.append(initial_entry)

    @property
    def _curr(self) -> API.ReportStackEntry_d:
        return self._stack[-1]

    @property
    def log(self) -> Logger:
        match self._logger:
            case None:
                return logging
            case x:
                return x

    @log.setter
    def log(self, logger:Maybe[Logger]) -> None:
        match logger:
            case None:
                self._logger = logging
            case logmod.Logger():
                self._logger = logger
            case x:
                raise TypeError(type(x))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} : {self.log.name} : {self.log.level} >"

    def active_level(self, level:int) -> None:
        """ Set the base level the reporter will log at. """
        self._curr.log_level = level

    def set_state(self, state:str, **kwargs:Any) -> Self:
        new_top         = deepcopy(self._stack[-1])
        new_top.data    = dict(kwargs)
        new_top.state   = state
        self._stack.append(new_top)
        logging.info("Report State Set To: %s", state)
        return self

    def pop_state(self) -> None:
        self._stack.pop()

    def add_trace(self, msg:str, *args:Any, flags:Any=None) -> None:
        pass

    def __enter__(self) -> Self:
        self._entry_count += 1
        return self

    def __exit__(self, *exc:Any) -> bool:
        match self._entry_count:
            case int() as x if x < 1:
                raise ValueError("Reporter enter/exit pairs count has gone negative")
            case int() as x if x != len(self._stack):
                raise ValueError("Mismatch between reporter stack and enter/exit pairs")
            case _:
                self._entry_count -= 1
                self.pop_state()

        match exc:
            case (None, None, None):
                return True
            case _:
                return False

    def _out(self, key:str, *, info:Maybe[str]=None, msg:Maybe[str]=None, level :int=0) -> None:
        """ The reporter delegates all actual logging to this method

        """
        assert(isinstance(self._logger, logmod.Logger)), self._logger
        result = self._fmt(key, info=info, msg=msg, ctx=self.ctx)
        self._logger.log(self._curr.log_level+level, result)
