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

@Proto(API.ReportFormatter_p)
class ReportFormatter:
    """ ReportFormatter abstracts the logic of creating a contextual message.

    """

    def __init__(self, *, segments:Maybe[dict]=None):
        self._segments         = (segments or API.TRACE_LINES_ASCII).copy()
        self.line_fmt          = API.LINE_PASS_FMT
        self.msg_fmt           = API.LINE_MSG_FMT
        self._process_segments()

    def __call__(self, key:str, *, info:Maybe[str]=None, msg:Maybe[str]=None, ctx:Maybe[list]=None) -> str:
        """ Build the formatted report line.

        key : the segment type to use
        info/msg : values to format into the report
        ctx : list[str] of values prefixing the report
        """
        extra        = {}
        extra['time']= datetime.datetime.now().strftime(API.TIME_FMT) # noqa: DTZ005
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
            case str() if not bool(msg) and not bool(info):
                fmt = self.line_fmt
            case _:
                fmt              = self.msg_fmt
                extra['info']    = str(info or "")
                extra['detail']  = str(msg)
                # Ensure the same gap between the end of the info, and start of the msg
                extra['gap2'] = " "*max(1, (API.MSG_SPACING - len(extra['info'])))

        extra['ctx'] = self._build_ctx(ctx)
        result : str = fmt.format_map(extra)
        return result

    def get_segment(self, key:str) -> Maybe[str]:
        match self._segments.get(key, None):
            case None:
                return None
            case str() as val:
                return val
            case left, mid, right:
                return None
            case _:
                raise ValueError("Unexpected value in reporter segments", key)

    ##--|
    def _process_segments(self):
        """ Ensure all needed segments exist and are the right size

        if any are missing, use doot.reporters._interface.TRACE_LINES_ASCII's values
        """
        processed = {}
        for x,y in API.TRACE_LINES_ASCII.items():
            processed.setdefault(x, y)
        else:
            start_i, mid_i, end_i = API.SEGMENT_SIZES
            just_char = self._segments.get("just_char", API.TRACE_LINES_ASCII["just_char"])
        for x,y in self._segments.items():
            match y:
                case str():
                    processed[x] = y
                case start, mid, end:
                    processed[x] = (start.ljust(start_i, just_char),
                                    mid.ljust(mid_i, just_char),
                                    end.ljust(end_i, just_char))
                case other:
                    raise ValueError("Unexpected segment", other)

        else:
            self._segments = processed

    def _build_ctx(self, ctx:Maybe[list]) -> str:
        """ Given a current context list, builds a prefix string for the current print call """
        match ctx:
            case None | []:
                return ""
            case list():
                return API.GAP.join(ctx) + API.GAP
            case x:
                raise TypeError(type(x))
