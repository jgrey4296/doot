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

from jgdv import Proto, Mixin
import doot
from . import _interface as API
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
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
logging.setLevel(logmod.CRITICAL)
##-- end logging

# Vars:
LINE_LEN  : Final[int] = 46
LINE_CHAR : Final[str] = "-"
# Body:

class _WorkflowReporter_m:

    def root(self) -> None:
        self._out("root")

    def wait(self) -> None:
        self._out("wait")

    def act(self, info:str, msg:str) -> None:
        self._out("act", info=info, msg=msg)

    def fail(self, info:str, msg:str) -> None:
        self._out("fail")

    def branch(self, name:str) -> Self:
        self._out("branch")
        self.ctx += [self._segments['inactive'], self._segments['gap']]
        self._out("begin", info=name, msg="")
        return self

    def pause (self, reason:str) -> Self:
        self.ctx.pop()
        self.ctx.pop()
        self._out("pause", msg=reason)
        return self

    def result(self, state:list[str]) -> Self:
        self.ctx.pop()
        self.ctx.pop()
        self._out("result", msg=state)
        return self

    def resume(self, name:str) -> Self:
        self._out("resume", msg=name)
        self.ctx += [self._segments['inactive'], self._segments['gap']]
        return self

    def finished(self) -> None:
        self._out("finished")

    def queue(self, num:int) -> None:
        pass

    def state_result(self, *vals:str) -> None:
        pass

class _GenReporter_m:

    def set_state(self, state, **kwargs) -> None:
        self._state_data = dict(kwargs)
        self._state      = state
        logging.info("Report State Set To: %s", state)


    def gap(self) -> None:
        self.log.user("")

    def line(self, msg:Maybe[str]=None) -> None:
        match msg:
            case str() as x:
                val = x.strip()
                val = val.center(len(val) + 4, " ")
                val = val.center(LINE_LEN, LINE_CHAR)
                self.log.user(val, extra=self._log_extra)
            case _:
                self.log.user(LINE_CHAR*LINE_LEN, extra=self._log_extra)

    def header(self) -> None:
        self.active_level(logmod.WARN)
        self._log_extra['colour'] = "green"
        self.line()
        self.line("Doot")
        self.line()
        # HEADER_MSG   = doot.constants.printer.doot_header
        # self.log.user(HEADER_MSG, extra={"colour": "green"})

    def summary(self) -> None:
        self.active_level(logmod.WARN)
        match self._state:
            case "fail":
                self._log_extra['colour'] = "red"
                msg = doot.config.on_fail("Errored").shutdown.notify.fail_msg()
            case _:
                msg = doot.config.on_fail("Success").shutdown.notify.success_msg()

        self.line(msg)
        # TODO the report
        self.gap()

    def user(self, msg, *rest, **kwargs) -> None:
        self.log.warning(msg, *rest)

    def trace(self, msg, *rest, **kwargs) -> None:
        self.log.info(msg, *rest)

    def failure(self, msg, *rest, **kwargs) -> None:
        self.log.exception(msg, *rest)

    def warn(self, msg, *rest, **kwargs) -> None:
        self.log.warn(msg, *rest)

    def error(self, msg, *rest, **kwargs) -> None:
        self.log.error(msg, *rest)

    def detail(self, msg, *rest, **kwargs) -> None:
        self.log.debug(msg, *rest)


##--|
@Proto(API.WorkflowReporter_p, API.GeneralReporter_p)
@Mixin(_GenReporter_m, _WorkflowReporter_m)
class NullReporter(API.Reporter_d):
    """ The initial reporter for prior to configuration """

    def __init__(self, *args, logger:Maybe[Logger]=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._logger            = logger
        self._log_level         = logmod.ERROR
        self._segments          = API.TRACE_LINES_ASCII.copy()
        self._fmt               = TraceFormatter()
        self.level              = 0
        self.ctx                = []
        self._act_trace         = []
        self._state             = None
        self._state_data        = {}
        self._log_extra         = {"colour":"blue"}

    @property
    def log(self) -> Logger:
        match self._logger:
            case None:
                return logging
            case x:
                return x

    @log.setter
    def log(self, logger:Logger) -> None:
        match logger:
            case logmod.Logger():
                self._logger = logger
                self._logger.setLevel(self._log_level)
            case x:
                raise TypeError(type(x))


    def active_level(self, level:int) -> None:
        self._log_level = level
        self.log.setLevel(level)

    def add_trace(self, msg:str, *args:Any, flags:Any=None) -> None:
        pass

    def __enter__(self) -> Self:
        self.level += 1
        return self

    def __exit__(self, *exc:Any) -> bool:
        self.level -= 1
        match exc:
            case (None, None, None):
                return True
            case _:
                return False

    def _build_ctx(self) -> str:
        return "".join(self.ctx)

    def _out(self, key:str, *, info:Maybe[str]=None, msg:Maybe[str]=None) -> None:
        return None
