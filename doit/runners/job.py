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

try:
    import cloudpickle
    pickle_dumps = cloudpickle.dumps
except ImportError:
    pickle_dumps = pickle.dumps

# JobXXX objects send from main process to sub-process for execution
class JobHold:
    """Indicates there is no task ready to be executed"""
    type = object()

class JobTask:
    """Contains a Task object"""
    type = object()
    def __init__(self, task):
        self.name = task.name
        try:
            self.task_pickle = pickle_dumps(task)
        # bug on python raising AttributeError
        # https://github.com/python/cpython/issues/73373
        except (pickle.PicklingError, AttributeError) as excp:
            msg = """Error on Task: `{}`.
Task created at execution time that has an attribute than can not be pickled,
so not feasible to be used with multi-processing. To fix this issue make sure
the task is pickable or just do not use multi-processing execution.

Original exception {}: {}
"""
            raise InvalidTask(msg.format(self.name, excp.__class__, excp))
