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


class TaskTimeout:
    """add timeout to task

    @param timeout_limit: (datetime.timedelta, int) in seconds

    if the time elapsed since last time task was executed is bigger than
    the "timeout" time the task is NOT up-to-date
    """

    def __init__(self, timeout_limit):
        if isinstance(timeout_limit, datetime.timedelta):
            self.limit_sec = ((timeout_limit.days * 24 * 3600)
                              + timeout_limit.seconds)
        elif isinstance(timeout_limit, int):
            self.limit_sec = timeout_limit
        else:
            msg = "timeout should be datetime.timedelta or int got %r "
            raise Exception(msg % timeout_limit)

    def __call__(self, task, values):

        def save_now():
            return {'success-time': time_module.time()}
        task.value_savers.append(save_now)
        last_success = values.get('success-time', None)
        if last_success is None:
            return False
        return (time_module.time() - last_success) < self.limit_sec
