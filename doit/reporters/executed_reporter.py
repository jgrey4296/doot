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


class ExecutedOnlyReporter(ConsoleReporter):
    """No output for skipped (up-to-date) and group tasks

    Produces zero output unless a task is executed
    """
    desc = 'console, no output for skipped (up-to-date) and group tasks'

    def skip_uptodate(self, task):
        """skipped up-to-date task"""
        pass

    def skip_ignore(self, task):
        """skipped ignored task"""
        pass
