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

class TimestampCheck:
    """check if timestamp of a given file/dir is unchanged since last run.

    The C{cmp_op} parameter can be used to customize when timestamps are
    considered unchanged, e.g. you could pass L{operator.ge} to also consider
    e.g. files reverted to an older copy as unchanged; or pass a custom
    function to completely customize what unchanged means.

    If the specified file does not exist, an exception will be raised.  Note
    that if the file C{fn} is a target of another task you should probably add
    C{task_dep} on that task to ensure the file is created before checking it.
    """

    def __init__(self, file_name, time='mtime', cmp_op=operator.eq):
        """initialize the callable

        @param fn: (str) path to file/directory to check
        @param time: (str) which timestamp field to check, can be one of
                     (atime, access, ctime, status, mtime, modify)
        @param cmp_op: (callable) takes two parameters (prev_time, current_time)
                   should return True if the timestamp is considered unchanged

        @raises ValueError: if invalid C{time} value is passed
        """
        if time in ('atime', 'access'):
            self._timeattr = 'st_atime'
        elif time in ('ctime', 'status'):
            self._timeattr = 'st_ctime'
        elif time in ('mtime', 'modify'):
            self._timeattr = 'st_mtime'
        else:
            raise ValueError('time can be one of: atime, access, ctime, '
                             'status, mtime, modify (got: %r)' % time)
        self._file_name = file_name
        self._cmp_op = cmp_op
        self._key = '.'.join([self._file_name, self._timeattr])

    def _get_time(self):
        return getattr(os.stat(self._file_name), self._timeattr)

    def __call__(self, task, values):
        """register action that saves the timestamp and check current timestamp

        @raises OSError: if cannot stat C{self._file_name} file
                         (e.g. doesn't exist)
        """

        def save_now():
            return {self._key: self._get_time()}
        task.value_savers.append(save_now)

        prev_time = values.get(self._key)
        if prev_time is None:  # this is first run
            return False
        current_time = self._get_time()
        return self._cmp_op(prev_time, current_time)

# action class

# debug helper
