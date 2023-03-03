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

class ZeroReporter(ConsoleReporter):
    """Report only internal errors from doit"""
    desc = 'report only internal errors from doit'

    def _just_pass(self, *args):
        """over-write base to do nothing"""
        pass

    get_status = execute_task = add_failure = add_success \
        = skip_uptodate = skip_ignore = teardown_task = complete_run \
        = _just_pass

    def runtime_error(self, msg):
        sys.stderr.write(msg)
