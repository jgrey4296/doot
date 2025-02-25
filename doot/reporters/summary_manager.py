#!/usr/bin/env python3
"""


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
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 1st party imports
from doot._abstract import Reporter_p
from doot.enums import Report_f
from doot.reporters.core.reporter import BaseReporter
from doot.structs import TraceRecord

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@dataclass
class ReportElement:
    name  : str
    succ  : int = 0
    fail  : int = 0
    skip  : int = 0
    total : int = 0

class DootReportManagerSummary(BaseReporter):
    """
    Groups job,task,action success and failures, returns information on them

    """

    def __init__(self, reporters:list=None):
        super().__init__(reporters)

    def __str__(self):
        report = self.generate_report()
        output = [
            "    - Totals : Jobs: {}, Tasks: {}, Actions: {}".format(report['jobs'].total, report['tasks'].total, report['actions'].total),
            "    - Success/Failures/Skips:",
            "    -- Jobs      : {}/{}/{}".format(report['jobs'].succ,report['jobs'].fail, report['jobs'].skip),
            "    -- Tasks     : {}/{}/{}".format(report['tasks'].succ, report['tasks'].fail, report['tasks'].skip),
            "    -- Actions   : {}/{}".format(report['actions'].succ, report['actions'].fail),
            "    -- Artifacts : {}".format(report['artifacts'].total),
        ]
        return "\n".join(output)

    def generate_report(self) -> dict[str,ReportElement]:
        report = {
            "tasks"     : ReportElement("tasks"),
            "jobs"      : ReportElement("jobs"),
            "actions"   : ReportElement("actions"),
            "artifacts" : ReportElement("artifacts"),
            "total"     : ReportElement("total"),
            }

        for trace in self._full_trace:
            report['total'].total += 1
            if Report_f.ARTIFACT in trace.flags:
                report['artifacts'].total += 1
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
                report[category].fail += 1
            if Report_f.SUCCEED in trace.flags:
                report[category].succ += 1
            if Report_f.SKIP in trace.flags:
                report[category].skip += 1

        return report
