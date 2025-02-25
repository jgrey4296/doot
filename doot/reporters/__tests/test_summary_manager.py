#!/usr/bin/env python3
"""

"""
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import warnings

import pytest

import doot

from doot.reporters.summary_manager import DootReportManagerSummary
from doot.enums import Report_f
from doot.structs import TraceRecord
from doot._abstract import Reporter_p

logging = logmod.root

class TestSummaryReporter:

    def test_initial(self):
        manager = DootReportManagerSummary()
        assert(isinstance(manager, Reporter_p))

    def test_add_basic_trace(self):
        manager = DootReportManagerSummary()
        assert(not bool(manager._full_trace))
        manager.add_trace("test")
        assert(bool(manager._full_trace))
        assert(isinstance(manager._full_trace[0], TraceRecord))

    def test_multi_add(self):
        manager = DootReportManagerSummary()
        assert(not bool(manager._full_trace))
        manager.add_trace("test")
        manager.add_trace("test")
        manager.add_trace("test")
        assert(len(manager._full_trace) == 3)
        assert(all(isinstance(x, TraceRecord) for x in manager._full_trace))

    def test_empty_generate_report(self):
        manager = DootReportManagerSummary()
        report = manager.generate_report()
        assert(isinstance(report, dict))
        assert(len(report) == 5)
        assert("tasks"     in report)
        assert("jobs"      in report)
        assert("actions"   in report)
        assert("artifacts" in report)
        assert("total"     in report)

    def test_generate_report(self):
        manager = DootReportManagerSummary()
        manager.add_trace("test", flags=Report_f.SUCCEED | Report_f.TASK)
        manager.add_trace("test", flags=Report_f.SUCCEED | Report_f.TASK)
        manager.add_trace("test", flags=Report_f.FAIL    | Report_f.JOB)
        manager.add_trace("test", flags=Report_f.SKIP | Report_f.ACTION)
        report = manager.generate_report()
        assert(isinstance(report, dict))
        assert(len(report) == 5)
        assert(report['jobs'].fail == 1)
        assert(report['actions'].skip== 1)
        assert(report['tasks'].succ == 2)
        assert(report['total'].total == 4)
