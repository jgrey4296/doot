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

import tracemalloc
import datetime

Seconds  : TypeAlias = int
DateTime : TypeAlias = datetime.datetime

class HumanMixin:
    """
    Simple Mixin for human related functions
    """

    @staticmethod
    def human_sizes(val, format=False):
        return tracemalloc._format_size(val, format)

    @staticmethod
    def round_time(dt:DateTime=None, roundTo:Seconds=60) -> DateTime:
        """Round a datetime object to any time lapse in seconds
        dt : datetime.datetime object, default now.
        roundTo : Closest number of seconds to round to, default 1 minute.
        Author: Thierry Husson 2012 - Use it as you want but don't blame me.
        from: https://stackoverflow.com/questions/3463930
        """
        dt       = dt or datetime.datetime.now()
        seconds  = (dt.replace(tzinfo=None) - dt.min).seconds
        rounding = (seconds+roundTo/2) // roundTo * roundTo
        return dt + datetime.timedelta(0,rounding-seconds,-dt.microsecond)
