#!/usr/bin/env python3
"""


"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 1st party imports
from doot._structs.artifact import TaskArtifact
from doot._structs.task_spec import TaskSpec
from doot._structs.action_spec import ActionSpec
from doot._structs.relation_spec import RelationSpec
from doot._structs.task_name import TaskName
from doot._structs.trace import TraceRecord


# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from doot._abstract import ReportLine_p

##--|
from doot._abstract import Reporter_p, Task_p
# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class BaseReporter(Reporter_p):

    def __init__(self, reporters:Maybe[list[ReportLine_p]]=None):
        self._full_trace     : list[TraceRecord]       = []
        self._reporters      : list[ReportLine_p]      = list(reporters or [self._default_formatter])

    def _default_formatter(self, trace:TraceRecord) -> str:
        return str(trace)

    def __str__(self):
        raise NotImplementedError()

    def add_trace(self, msg, *args, flags=None):
        match msg:
            case str():
                pass
            case TaskArtifact():
                msg = str(msg)
            case ActionSpec():
                msg = str(msg)
            case RelationSpec():
                msg = str(msg)
            case TaskSpec():
                msg = msg.name.readable
            case Task_p():
                msg = msg.shortname

        self._full_trace.append(TraceRecord(message=msg, flags=flags, args=args))
