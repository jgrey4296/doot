#!/usr/bin/env python3
"""


See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
# import more_itertools as mitz
# from boltons import
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doot._abstract.reporter import Reporter_p
from doot._structs.trace import DootTraceRecord

class BaseReporter(Reporter_p):

    def __init__(self, reporters:list[ReportLine_i]=None):
        self._full_trace     : list[DootTraceRecord]       = []
        self._reporters      : list[ReportLine_i] = list(reporters or [self._default_formatter])

    def _default_formatter(self, trace:DootTraceRecord) -> str:
        return str(trace)

    def __str__(self):
        raise NotImplementedError()

    def add_trace(self, msg, *args, flags=None):
        self._full_trace.append(DootTraceRecord(message=msg, flags=flags, args=args))
