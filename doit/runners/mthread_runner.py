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

class MThreadRunner(MRunner):
    """Parallel runner using threads"""
    Queue = staticmethod(queue.Queue)
    class DaemonThread(Thread):
        """daemon thread to make sure process is terminated if there is
        an uncatch exception and threads are not correctly joined.
        """
        def __init__(self, *args, **kwargs):
            Thread.__init__(self, *args, **kwargs)
            self.daemon = True
    Child = staticmethod(DaemonThread)

    @staticmethod
    def available():
        return True
