#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from tomler import Tomler
from doot.enums import ReportEnum
from doot.structs import DootTraceRecord

class Reporter_i:
    """
    Reporters, like loggers, are stacked, and each takes the flags and data and maybe runs.
    """

    @abc.abstractmethod
    def report(self, flags:ReportEnum, *args):
        raise NotImplementedError(self.__class__, "report")
