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
from doot._abstract import Reporter_i
from doot.reporters.stack_manager import DootReportManagerStack
from doot.structs import DootTraceRecord
from doot.enums import ReportEnum

logging = logmod.root

##-- pytest reminder
# caplog
# mocker.patch | patch.object | patch.multiple | patch.dict | stopall | stop | spy | stub
# pytest.mark.filterwarnings
# pytest.parameterize
# pytest.skip | skipif | xfail
# with pytest.deprecated_call
# with pytest.raises
# with pytest.warns(warntype)

##-- end pytest reminder

class TestReportStackManager:

    def test_initial(self):
        manager = DootReportManagerStack()
        assert(isinstance(manager, Reporter_i))


    def test_add_basic_trace(self):
        manager = DootReportManagerStack()
        assert(not bool(manager._full_trace))
        manager.trace("test")
        assert(bool(manager._full_trace))
        assert(isinstance(manager._full_trace[0], DootTraceRecord))

    def test_multi_add(self):
        manager = DootReportManagerStack()
        assert(not bool(manager._full_trace))
        manager.trace("test")
        manager.trace("test")
        manager.trace("test")
        assert(len(manager._full_trace) == 3)
        assert(all(isinstance(x, DootTraceRecord) for x in manager._full_trace))


    def test_str(self):
        manager = DootReportManagerStack()
        manager.trace("test")
        manager.trace("test")
        manager.trace("test")
        assert(str(manager) == "test\ntest\ntest")


    def test_custom_formatter(self):
        class SimpleFormatter:
            def __call__(self, trace):
                return "- {}".format(trace)

        manager = DootReportManagerStack([SimpleFormatter()])
        manager.trace("test")
        manager.trace("test")
        manager.trace("test")
        assert(str(manager) == "- test\n- test\n- test")


    def test_custom_filter(self):
        class SimpleFilter:
            def __call__(self, trace):
                if ReportEnum.TASK in trace.flags:
                    return str(trace)

        manager = DootReportManagerStack([SimpleFilter()])
        manager.trace("first", flags=ReportEnum.TASK)
        manager.trace("second", flags=ReportEnum.JOB)
        manager.trace("third", flags=ReportEnum.TASK)
        assert(str(manager) == "first\nthird")


    def test_multi_filter(self):
        class SimpleTaskFilter:
            def __call__(self, trace):
                if trace.flags in ReportEnum.TASK:
                    return str(trace)

        class SimpleActionFilter:
            def __call__(self, trace):
                if trace.flags in ReportEnum.ACTION:
                    return str(trace)

        manager = DootReportManagerStack([ SimpleTaskFilter(), SimpleActionFilter() ])
        manager.trace("first", flags=ReportEnum.TASK)
        manager.trace("second", flags=ReportEnum.JOB)
        manager.trace("third", flags=ReportEnum.ACTION)
        assert(str(manager) == "first\nthird")


    def test_combined_filter_formatter(self):
        class SimpleTaskFilter:
            def __call__(self, trace):
                if trace.flags in ReportEnum.TASK:
                    return str(trace)

        class SimpleActionFilter:
            def __call__(self, trace):
                if trace.flags in ReportEnum.ACTION:
                    return "- {}".format(trace)

        manager = DootReportManagerStack([ SimpleTaskFilter(), SimpleActionFilter() ])
        manager.trace("first", flags=ReportEnum.TASK)
        manager.trace("second", flags=ReportEnum.JOB)
        manager.trace("third", flags=ReportEnum.ACTION)
        assert(str(manager) == "first\n- third")
