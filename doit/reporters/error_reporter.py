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

class ErrorOnlyReporter(ZeroReporter):
    desc = """Report only errors internal or TaskError and TaskFailure."""

    def add_failure(self, task, fail_info: BaseFail):
        if not fail_info.report:
            return
        exception_name = fail_info.get_name()
        self.write(f'taskid:{task.name} - {exception_name}\n')
        self.write(fail_info.get_msg())
        self.write("\n")
