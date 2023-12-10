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

from doot._abstract import FailPolicy_p

class BreakerPolicy(FailPolicy_p):
    pass

class BulkheadPolicy(FailPolicy_p):
    pass

class RetryPolicy(FailPolicy_p):
    pass

class TimeoutPolicy(FailPolicy_p):
    pass

class CachePolicy(FailPolicy_p):
    pass

class FallBackPolicy(FailPolicy_p):

    def __init__(self, *policies:FailPolicy_p):
        self._policy_stack = list(policies)

    def __call__(self, *args, **kwargs):
        return False

class CleanupPolicy(FailPolicy_p):
    pass

class DebugPolicy(FailPolicy_p):

    def __call__(self, *args, **kwargs):
        breakpoint()
        pass
        return False

class PretendPolicy(FailPolicy_p):
    pass

class AcceptPolicy(FailPolicy_p):
    pass
