#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
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

from doot._abstract import Reporter_i, ReportLine_i
from doot.structs import DootTraceRecord
from doot.enums import ReportEnum

class DootReportManagerSummary(Reporter_i):
    """
    Groups job,task,action success and failures, returns information on them

    """

    def __init__(self, reporters:list=None):
        super().__init__(reporters)

    def __str__(self):
        result = {
            "tasks"     : {"success": 0, "fail": 0, "total": 0},
            "actions"   : {"success": 0, "fail": 0, "total": 0},
            "jobs"      : {"success": 0, "fail": 0, "total": 0},
            "artifacts" : 0
            }

        for trace in self._full_trace:
            if ReportEnum.ARTIFACT in trace.flags:
                result['artifacts'] += 1
                continue

            category = None
            ended   = None

            if ReportEnum.JOB in trace.flags:
                category = "jobs"
            elif ReportEnum.ACTION in trace.flags:
                category = "actions"
            elif ReportEnum.TASK in trace.flags:
                category = "tasks"

            if ReportEnum.FAIL in trace.flags:
                ended = "fail"
            elif ReportEnum.SUCCEED in trace.flags:
                ended = "success"

            if category is None or ended is None:
                continue

            result[category][ended] += 1
            result[category]["total"] += 1

        output = [
            "    - Totals : Jobs: {}, Tasks: {}, Actions: {}".format(result['jobs']['total'], result['tasks']['total'], result['actions']['total']),
            "    - Success/Failures:",
            "    -- Jobs      : {}/{}".format(result['jobs']['success'],result['jobs']['fail']),
            "    -- Tasks     : {}/{}".format(result['tasks']['success'], result['tasks']['fail']),
            "    -- Actions   : {}/{}".format(result['actions']['success'], result['actions']['fail']),
            "    -- Artifacts : {}".format(result['artifacts']),
        ]
        return "\n".join(output)
