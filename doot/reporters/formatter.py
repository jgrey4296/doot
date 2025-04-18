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

from jgdv import Proto
from . import _interface as API

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
##-- end logging

# Vars:

# Body:

@Proto(API.TraceFormatter_p)
class TraceFormatter:

    def __init__(self):
        self._segments         = API.TRACE_LINES_ASCII.copy()
        self.line_fmt          = API.LINE_PASS_FMT
        self.msg_fmt           = API.LINE_MSG_FMT

    def _build_ctx(self, ctx:Maybe[list]) -> str:
        """ Given a current context list, builds a prefix string for the current print call """
        match ctx:
            case None:
                return ""
            case list():
                return "".join(ctx)
            case x:
                raise TypeError(type(x))

    def __call__(self, key:str, *, info:Maybe[str]=None, msg:Maybe[str]=None, ctx:Maybe[list]=None) -> str:
        """ Build the formatted report line.

        """
        extra        = {}
        extra['time']= datetime.datetime.now().strftime("%H:%M")  # noqa: DTZ005
        match self._segments.get(key, None):
            case str() if key in self._segments:
                extra['act'] = self._segments[key]
                extra['gap'] = " "*max(1, (API.ACT_SPACING - len(extra['act'])))
            case (str() as l, str() as m, str() as r):
                # Ensure the same gap between the end of the act, and start of the info
                extra['act'] = f"{l}{m}{r}"
                extra['gap'] = " "*max(1, (API.ACT_SPACING - len(r)))
            case x:
                raise TypeError(type(x))

        match msg:
            case None:
                fmt = self.line_fmt
            case str():
                fmt           = self.msg_fmt
                extra['info'] = info or ""
                # Ensure the same gap between the end of the info, and start of the msg
                extra['gap2'] = " "*max(1, (API.MSG_SPACING - len(extra['info'])))
                extra['detail']  = msg
            case x:
                raise TypeError(type(x))

        extra['ctx'] = self._build_ctx(ctx)
        result : str = fmt.format_map(extra)
        return result
