#!/usr/bin/env python3
"""

"""
# ruff: noqa:
# mypy: disable-error-code="attr-defined"
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import atexit#  for @atexit.register
import collections
import contextlib
import datetime
import enum
import faulthandler
import functools as ftz
import hashlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import sys
import time
import types
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Mixin, Proto
from jgdv.logging._interface import PRINTER_NAME

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot

# ##-- end 1st party imports

# ##-| Local
from . import _interface as API  # noqa: N812
from .formatter import ReportFormatter

# # End of Imports.

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

    from logmod import Logger
    from ._interface import Reporter_p
    from doot.workflow._interface import TaskName_p
    type TreeElem = None | str | list[TreeElem] | dict[str, TreeElem] | tuple[str, TreeElem]
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
logging.setLevel(logmod.WARN)
##-- end logging

# Vars:
LINE_LEN        : Final[int]  = 46
LINE_CHAR       : Final[str]  = "-"
INIT_LEVEL      : Final[int]  = logmod.WARN
START_COUNT     : Final[int]  = 0
DEFAULT_HEADER  : Final[str]  = "Doot"
# Body:

class BaseGroup:

    _log : Logger
    _fmt : API.ReportFormatter_p

    _lvl : int

    def __init__(self, *, log:Logger, fmt:ReportFormatter, lvl:int=logmod.DEBUG) -> None:
        self._log          = log
        self._fmt          = fmt
        self._lvl          = lvl
        self._entry_count  = 0
        self._stack        = [
            API.ReportStackEntry_d(state="initial",
                                   data={},
                                   log_extra={"colour":"blue"},
                                   log_level=INIT_LEVEL,
                                   ),
            ]

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

    @property
    def state(self) -> API.ReportStackEntry_d:
        return self._stack[-1]

    def _out(self, key:str, *, info:Maybe=None, msg:Maybe=None, level:int=0) -> None:
        """ reporter groups delegate formatting and logging/printing to this method """
        result = self._fmt(key, info=info, msg=msg, ctx=self.state.prefix)
        self._log.log(self._lvl+level, result)

    def push_state(self, state:str, **kwargs:Any) -> Self:
        new_top  : API.ReportStackEntry_d
        new_top       = deepcopy(self._stack[-1])
        new_top.data  = dict(kwargs)
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

    def gap(self) -> Self:
        self._log.info("")
        return self

    def line(self, msg:Maybe[str]=None, char:Maybe[str]=None) -> Self:
        char = char or LINE_CHAR
        match msg:
            case str() as x:
                val = x.strip()
                val = val.center(len(val) + 4, " ")
                val = val.center(LINE_LEN, char)
                self._log.info(val)
            case _:
                self._log.info(char*LINE_LEN)

        return self

class TreeGroup(BaseGroup, API.TreeGroup_p):
    """ Methods to report a tree of data.

    eg: a tree of jobs/tasks and their dependencies

    data format is a nesting of list,
    where each sublist is a branch
    """
    _labels : dict

    def __init__(self, **kwargs:Any) -> None:
        super().__init__(**kwargs)
        self._labels = {
            "root"    : "Root",
            "branch"  : "Branch",
            "leaf"    : "Leaf",
            "end"     : "End",
        }

    def _label(self, key:str) -> str:
        return self._labels.get(key, key)

    def tree(self, data:dict|list, *, title:Maybe[str]=None) -> Self:
        queued : list[TreeElem] = [data]
        self.root(title=title)
        while bool(queued):
            curr = queued.pop()
            match curr:
                case None:
                    self.unbranch()
                case str() as x, list() as y:
                    self.branch(x)
                    queued.append(None)
                    queued +=  reversed(y)
                case str() as x, dict() as y:
                    self.branch(x)
                    queued.append(None)
                    queued +=  reversed(y.items())
                case str() as x:
                    self.leaf(x)
                case list() | dict() if not bool(curr):
                    pass
                case dict() as x:
                    queued += reversed(x.items())
                case [*xs]:
                    queued += reversed(xs)
        else:
            self.finished()
            return self

    def root(self, title:Maybe[str]=None) -> Self:
        self._out("root", info=self._label("root"), msg=title)
        return self

    def branch(self, name:str|TaskName_p, info:Maybe[str]=None) -> Self:
        self._out("branch")
        self._out("begin", info=self._label(info or "branch"), msg=name)
        self.push_state("branch")
        return self

    def leaf(self, msg:str, level:int=0) -> Self:
        self._out("act", info=self._label("leaf"), msg=msg)
        return self

    def unbranch(self) -> Self:
        self._out("finished")
        self.pop_state()
        return self

    def finished(self) -> Self:
        self._out("finished", info=self._label("end"), msg="")
        return self

class WorkflowGroup(BaseGroup, API.WorkflowGroup_p):
    """ Methods for reporting the progress of a workflow

    eg: marking start/end of workflow, entry/exit of tasks,
    action content...
    """

    @override
    def root(self) -> Self:
        self._out("root", level=6)
        return self

    @override
    def wait(self) -> Self:
        self._out("wait")
        return self

    @override
    def act(self, info:str, msg:str, level:int=0) -> Self:
        self._out("act", info=info, msg=msg, level=level)
        return self

    @override
    def branch(self, name:str|TaskName_p, info:Maybe[str]=None) -> Self:
        self._out("branch", level=5)
        self._out("begin", info=info or "Start", msg=name, level=5)
        self.push_state("branch")
        return self

    @override
    def resume(self, name:str|TaskName_p) -> Self:
        self._out("resume", msg=name, level=5)
        self.push_state("resume")
        return self

    @override
    def pause (self, reason:str) -> Self:
        self.pop_state()
        self._out("pause", msg=reason, level=5)
        return self

    @override
    def result(self, state:list[str], info:Maybe[str]=None) -> Self:
        assert(isinstance(state, list))
        self.pop_state()
        self._out("result" , msg=",".join(str(x) for x in state), info=info, level=5)
        return self

    @override
    def fail(self, *, info:Maybe[str]=None, msg:Maybe[str]=None) -> Self:
        self.pop_state()
        self._out("fail", info=info, msg=msg, level=40)
        return self

    @override
    def finished(self) -> Self:
        self._out("finished", level=5)
        return self

    @override
    def queue(self, num:int) -> Self:
        raise NotImplementedError()

    @override
    def state_result(self, *vals:str) -> Self:
        raise NotImplementedError()

class GenGroup(BaseGroup, API.GeneralGroup_p):
    """ General user level messaging """

    @override
    def header(self, *, header:Maybe[str]=None) -> Self:
        self.line()
        self.line(header or DEFAULT_HEADER)
        self.line()
        return self

    @override
    def user(self,    msg:str, *rest:Any, **kwargs:Any) -> Self:
        self._log.warning(msg, *rest, **kwargs)
        return self

    @override
    def trace(self,   msg:str, *rest:Any, **kwargs:Any) -> Self:
        self._log.info(msg, *rest, **kwargs)
        return self

    @override
    def detail(self,  msg:str, *rest:Any, **kwargs:Any) -> Self:
        self._log.debug(msg, *rest, **kwargs)
        return self

    @override
    def failure(self, msg:str, *rest:Any, **kwargs:Any) -> Self:
        match doot.is_setup:
            case False:
                print(msg % rest, file=sys.stderr)
            case _:
                self._log.exception(msg, *rest, **kwargs)

        return self

    @override
    def warn(self,    msg:str, *rest:Any, **kwargs:Any) -> Self:
        match doot.is_setup:
            case False:
                print(msg % rest, file=sys.stderr)
            case _:
                self._log.warn(msg, *rest)

        return self

    @override
    def error(self,   msg:str, *rest:Any, **kwargs:Any) -> Self:
        match doot.is_setup:
            case False:
                print(msg % rest, file=sys.stderr)
            case _:
                self._log.error(msg, *rest)

        return self

class SummaryGroup(BaseGroup, API.SummaryGroup_p):
    """ A reporter group for producing a summary at end of the workflow.

    eg: success/failures, actions performed, time taken...
    """
    _start      : Maybe[DateTime]
    _end        : Maybe[DateTime]
    _subgroups  : dict[str, list]

    def __init__(self, **kwargs:Any) -> None:
        super().__init__(**kwargs)
        self._subgroups  = {}
        self._start      = None
        self._end        = None

    @override
    def start(self) -> None:
        """ Set the Start Time """
        raise NotImplementedError()

    @override
    def finish(self) -> None:
        """ Set the End Time """
        raise NotImplementedError()

    @override
    def add(self, key:str, *vals:Any) -> Self:
        """ Add a summary group value """
        raise NotImplementedError()

    @override
    def summarise(self, *, state:bool=True) -> Self:
        """ Output the summary that has been accumulated """
        msg : str
        match state:
            case False:
                self.state.log_extra['colour'] = "red"
                msg = doot.config.on_fail("Errored").shutdown.notify.fail_msg()
            case True:
                msg = doot.config.on_fail("Success").shutdown.notify.success_msg()

        self.line(msg)
        # TODO the report
        self.gap()
        return self

##--|

@Proto(API.Reporter_p)
class BasicReporter:
    """ The initial reporter for prior to configuration """

    def __init__(self, *args:Any, logger:Maybe[Logger]=None, segments:Maybe[dict]=None, **kwargs:Any) -> None:
        super().__init__(*args, **kwargs)

        self._entry_count  = START_COUNT
        self._fmt          = ReportFormatter(segments=segments or API.TRACE_LINES_ASCII)
        self._logger       = logger or logmod.getLogger(PRINTER_NAME)
        self._stack        = []
        self._tree         = TreeGroup(log=self._logger, fmt=self._fmt)
        self._workflow     = WorkflowGroup(log=self._logger, fmt=self._fmt)
        self._general      = GenGroup(log=self._logger, fmt=self._fmt)
        self._summary      = SummaryGroup(log=self._logger, fmt=self._fmt)

        initial_entry      = API.ReportStackEntry_d(state="initial",
                                                    data={},
                                                    log_extra={"colour":"blue"},
                                                    log_level=INIT_LEVEL,
                                                    )
        self._stack.append(initial_entry)

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} : {self.log.name} : {self.log.level} >"

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

    ##--|

    @property
    def state(self) -> API.ReportStackEntry_d:
        return self._stack[-1]

    @property
    def wf(self) -> API.WorkflowGroup_p:
        return self._workflow

    @property
    def gen(self) -> API.GeneralGroup_p:
        return self._general

    @property
    def tree(self) -> API.TreeGroup_p:
        return self._tree

    @property
    def summary(self) -> API.SummaryGroup_p:
        return self._summary

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

    ##--|

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
