#!/usr/bin/env python3
"""
The Basic implementation of a reporter.

_WorkflowReporter_m implements WorkflowReporter_p methods,
while _GenReporter_m implements GeneralReporter_p methods.

The BasicReporter has both:
- _stack
- _entry_count

The stack hold all ReportStackEntry_d's,
while the entry_count records the number of times the reporter has
been used in a 'with' statement.
This is to ensure that if you add entries to the stack,
you've got to pop them off before the end of the with block.

"""
# ruff: noqa:
# mypy: disable-error-code="attr-defined"
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

    from logmod import Logger
    from ._interface import Reporter_p
    type TreeElem = None | str | list[TreeElem] | dict[str, TreeElem] | tuple[str, TreeElem]
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
logging.setLevel(logmod.WARN)
##-- end logging

# Vars:
LINE_LEN    : Final[int] = 46
LINE_CHAR   : Final[str] = "-"
INIT_LEVEL  : Final[int] = logmod.WARN
START_COUNT : Final[int] = 0
# Body:

class _TreeReporter_m:
    """ Methods to report a tree of data


    """

    def tree(self:Reporter_p, data:dict|list) -> Reporter_p:
        queued : list[TreeElem] = [data]
        self.root()
        while bool(queued):
            curr = queued.pop()
            match curr:
                case None:
                    self.finished()
                case str() as x, list() as y:
                    self.branch(x, info="Branch")
                    queued.append(None)
                    queued +=  reversed(y)
                case str() as x, dict() as y:
                    self.branch(x, info="Branch")
                    queued.append(None)
                    queued +=  reversed(y.items())
                case str() as x:
                    self.act("Leaf", x)
                case list() | dict() if not bool(curr):
                    pass
                case dict() as x:
                    queued += reversed(x.items())
                case [*xs]:
                    queued += reversed(xs)
        else:
            self.finished()
            return self

class _WorkflowReporter_m:
    """ Methods for reporting the progress of a workflow """

    def root(self:Reporter_p) -> Reporter_p:
        self._out("root", level=6)
        return self

    def wait(self:Reporter_p) -> Reporter_p:
        self._out("wait")
        return self

    def act(self:Reporter_p, info:str, msg:str, level:int=0) -> Reporter_p:
        self._out("act", info=info, msg=msg, level=level)
        return self

    def branch(self:Reporter_p, name:str, info:Maybe[str]=None) -> Reporter_p:
        self._out("branch", level=5)
        self._out("begin", info=info or "Start", msg=name, level=5)
        self.push_state("branch")
        return self

    def resume(self:Reporter_p, name:str) -> Reporter_p:
        self._out("resume", msg=name, level=5)
        self.push_state("resume")
        return self

    def pause (self:Reporter_p, reason:str) -> Reporter_p:
        self.pop_state()
        self._out("pause", msg=reason, level=5)
        return self

    def result(self:Reporter_p, state:list[str], info:Maybe[str]=None) -> Reporter_p:
        assert(isinstance(state, list))
        self.pop_state()
        self._out("result" , msg=",".join(str(x) for x in state), info=info, level=5)
        return self

    def fail(self:Reporter_p, *, info:Maybe[str]=None, msg:Maybe[str]=None) -> Reporter_p:
        self.pop_state()
        self._out("fail", info=info, msg=msg, level=40)
        return self

    def finished(self:Reporter_p) -> Reporter_p:
        self._out("finished", level=5)
        return self

    def queue(self:Reporter_p, num:int) -> Reporter_p:
        raise NotImplementedError()

    def state_result(self:Reporter_p, *vals:str) -> Reporter_p:
        raise NotImplementedError()

class _GenReporter_m:
    """ General """
    log : Logger
    active_level : Callable

    def gap(self:Reporter_p) -> Reporter_p:
        self.log.info("")
        return self

    def line(self:Reporter_p, msg:Maybe[str]=None, char:Maybe[str]=None) -> Reporter_p:
        char = char or LINE_CHAR
        match msg:
            case str() as x:
                val = x.strip()
                val = val.center(len(val) + 4, " ")
                val = val.center(LINE_LEN, char)
                self.log.info(val)
            case _:
                self.log.info(char*LINE_LEN)

        return self

    def header(self:Reporter_p) -> Reporter_p:
        self.active_level(logmod.INFO)
        self.state.log_extra['colour'] = "green"
        self.line()
        self.line("Doot")
        self.line()
        return self

    def summary(self:Reporter_p) -> Reporter_p:
        msg : str
        self.active_level(logmod.WARN)
        match self.state.state:
            case "fail":
                self.state.log_extra['colour'] = "red"
                msg = doot.config.on_fail("Errored").shutdown.notify.fail_msg()
            case _:
                msg = doot.config.on_fail("Success").shutdown.notify.success_msg()

        self.line(msg)
        # TODO the report
        self.gap()
        return self

    def user(self:Reporter_p, msg:str, *rest:str, **kwargs:str) -> Reporter_p:
        self.log.warning(msg, *rest, **kwargs)
        return self

    def trace(self:Reporter_p, msg:str, *rest:str, **kwargs:str) -> Reporter_p:
        self.log.info(msg, *rest, **kwargs)
        return self

    def detail(self:Reporter_p, msg:str, *rest:str, **kwargs:str) -> Reporter_p:
        self.log.debug(msg, *rest, **kwargs)
        return self

    def failure(self:Reporter_p, msg:str, *rest:str, **kwargs:str) -> Reporter_p:
        match doot.is_setup:
            case False:
                print(msg % rest, file=sys.stderr)
            case _:
                self.log.exception(msg, *rest, **kwargs)

        return self

    def warn(self:Reporter_p, msg:str, *rest:str, **kwargs:str) -> Reporter_p:  # noqa: ARG002
        match doot.is_setup:
            case False:
                print(msg % rest, file=sys.stderr)
            case _:
                self.log.warn(msg, *rest)

        return self

    def error(self:Reporter_p, msg:str, *rest:str, **kwargs:str) -> Reporter_p:  # noqa: ARG002
        match doot.is_setup:
            case False:
                print(msg % rest, file=sys.stderr)
            case _:
                self.log.error(msg, *rest)

        return self

##--|

@Proto(API.Reporter_i)
@Mixin(_GenReporter_m, _WorkflowReporter_m, _TreeReporter_m, None, allow_inheritance=True)
class BasicReporter:
    """ The initial reporter for prior to configuration """

    def __init__(self, *args:Any, logger:Maybe[Logger]=None, segments:Maybe[dict]=None, **kwargs:Any) -> None:
        super().__init__(*args, **kwargs)
        self._entry_count       = START_COUNT
        self._fmt               = TraceFormatter(segments=segments or API.TRACE_LINES_ASCII)
        self._logger            = logger or logging
        self._stack             = []

        initial_entry           = API.ReportStackEntry_d(state="initial",
                                                         data={},
                                                         log_extra={"colour":"blue"},
                                                         log_level=INIT_LEVEL,
                                                         )
        self._stack.append(initial_entry)
        pass

    @property
    def state(self) -> API.ReportStackEntry_d:
        return self._stack[-1]

    @property
    def log(self) -> Logger:
        return self._logger

    @log.setter
    def log(self, logger:Maybe[Logger]) -> None:
        match logger:
            case None:
                self._logger = logging
            case logmod.Logger():
                self._logger = logger
            case x:
                raise TypeError(type(x))

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} : {self.log.name} : {self.log.level} >"

    def active_level(self, level:int) -> None:
        """ Set the base level the reporter will log at. """
        self.state.log_level = level

    def push_state(self, state:str, **kwargs:Any) -> Self:
        new_top : API.ReportStackEntry_d
        new_top         = deepcopy(self._stack[-1])
        new_top.data    = dict(kwargs)
        new_top.depth   += 1
        new_top.state   = state
        match self._fmt.get_segment("inactive"):
            case None:
                pass
            case str() as val:
                new_top.prefix.append(val)
        self._stack.append(new_top)
        logging.info("Report State Set To: %s", state)
        return self

    def pop_state(self) -> Self:
        match self._stack:
            case [x]:
                pass
            case _:
                self._stack.pop()

        return self

    def add_trace(self, msg:str, *args:Any, flags:Any=None) -> None:
        raise NotImplementedError()

    def __enter__(self) -> Self:
        self._entry_count += 1
        self.push_state("ctx_manager")
        return self

    def __exit__(self, *exc:Any) -> bool:
        match self._entry_count:
            case int() as x if x < 1:
                raise ValueError("Reporter enter/exit pairs count has gone negative")
            case int() as x if x != len(self._stack) - 1:
                raise ValueError("Mismatch between reporter stack and enter/exit pairs", x, len(self._stack))
            case _:
                self._entry_count -= 1
                self.pop_state()

        match exc:
            case (None, None, None):
                return True
            case _:
                return False

    def _out(self, key:str, *, info:Maybe[str]=None, msg:Maybe[str]=None, level:int=0) -> None:
        """ The reporter delegates all actual logging to this method

        """
        result = self._fmt(key, info=info, msg=msg, ctx=self.state.prefix)
        self._logger.log(self.state.log_level+level, result)
