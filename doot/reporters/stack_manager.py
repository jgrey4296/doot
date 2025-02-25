#!/usr/bin/env python3
"""

"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 1st party imports
from doot._abstract import Reporter_p, ReportLine_p
from doot.reporters.core.reporter import BaseReporter
from doot.structs import TraceRecord

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class DootReportManagerStack(BaseReporter):
    """
    A Stack of Reporters to try using.
    The First one that returns a DootTrace is used.
    """

    def __init__(self, reporters:list[ReportLine_p]=None):
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
