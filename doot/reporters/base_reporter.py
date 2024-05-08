#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 1st party imports
from doot._abstract.reporter import Reporter_p
from doot._structs.trace import DootTraceRecord
from doot._structs.artifact import DootTaskArtifact
from doot._structs.task_spec import DootTaskSpec
from doot._structs.action_spec import DootActionSpec
from doot._structs.relation_spec import RelationSpec
from doot._structs.task_name import DootTaskName
from doot._abstract.task import Task_i

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class BaseReporter(Reporter_p):

    def __init__(self, reporters:list[ReportLine_i]=None):
        self._full_trace     : list[DootTraceRecord]       = []
        self._reporters      : list[ReportLine_i] = list(reporters or [self._default_formatter])

    def _default_formatter(self, trace:DootTraceRecord) -> str:
        return str(trace)

    def __str__(self):
        raise NotImplementedError()

    def add_trace(self, msg, *args, flags=None):
        match msg:
            case str():
                pass
            case DootTaskArtifact():
                msg = str(msg)
            case DootActionSpec():
                msg = str(msg)
            case RelationSpec():
                msg = str(msg)
            case DootTaskSpec():
                msg = msg.name.readable
            case Task_i():
                msg = msg.shortname

        self._full_trace.append(DootTraceRecord(message=msg, flags=flags, args=args))
