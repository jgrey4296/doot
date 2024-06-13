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

from doot._abstract import Reporter_p
from doot.structs import TraceRecord
from doot.enums import Report_f
from doot.reporters.base_reporter import BaseReporter

class DootReportManagerSummary(BaseReporter):
    """
    Groups job,task,action success and failures, returns information on them

    """

    def __init__(self, reporters:list=None):
        super().__init__(reporters)

    def __str__(self):
        result = {
            "tasks"     : {"success": 0, "fail": 0, "skip": 0, "total": 0},
            "jobs"      : {"success": 0, "fail": 0, "skip": 0, "total": 0},
            "actions"   : {"success": 0, "fail": 0, "total": 0},
            "artifacts" : 0
            }

        for trace in self._full_trace:
            if Report_f.ARTIFACT in trace.flags:
                result['artifacts'] += 1
                continue

            category = None
            ended   = None

            if Report_f.JOB in trace.flags:
                category = "jobs"
            elif Report_f.ACTION in trace.flags:
                category = "actions"
            elif Report_f.TASK in trace.flags:
                category = "tasks"

            if Report_f.FAIL in trace.flags:
                ended = "fail"
            elif Report_f.SUCCEED in trace.flags:
                ended = "success"
            elif Report_f.SKIP in trace.flags:
                ended = "skip"

            if category is None or ended is None:
                continue

            result[category][ended] += 1
            result[category]["total"] += 1

        output = [
            "    - Totals : Jobs: {}, Tasks: {}, Actions: {}".format(result['jobs']['total'], result['tasks']['total'], result['actions']['total']),
            "    - Success/Failures/Skips:",
            "    -- Jobs      : {}/{}/{}".format(result['jobs']['success'],result['jobs']['fail'], result['jobs']['skip']),
            "    -- Tasks     : {}/{}/{}".format(result['tasks']['success'], result['tasks']['fail'], result['tasks']['skip']),
            "    -- Actions   : {}/{}".format(result['actions']['success'], result['actions']['fail']),
            "    -- Artifacts : {}".format(result['artifacts']),
        ]
        return "\n".join(output)
