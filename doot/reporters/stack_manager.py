#!/usr/bin/env python3
"""

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
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doot._abstract import Reporter_i, ReportLine_i
from doot.structs import DootTraceRecord

class DootReportManagerStack(Reporter_i):
    """
    A Stack of Reporters to try using.
    The First one that returns a DootTrace is used.
    """

    def __init__(self, reporters:list[ReportLine_i]=None):
        super().__init__(reporters)

    def __str__(self):
        result = []
        for trace in self._full_trace:
            for reporter in self._reporters:
                match reporter(trace):
                    case None:
                        continue
                    case str() as res:
                        result.append(res)

        return "\n".join(result)
