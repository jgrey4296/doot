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
doot._test_setup()

from doot._abstract import Reporter_p
from doot.reporters.stack_manager import DootReportManagerStack
from doot.structs import TraceRecord
from doot.enums import Report_f

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
        assert(isinstance(manager, Reporter_p))


    def test_add_basic_trace(self):
        manager = DootReportManagerStack()
        assert(not bool(manager._full_trace))
        manager.add_trace("test")
        assert(bool(manager._full_trace))
        assert(isinstance(manager._full_trace[0], TraceRecord))

    def test_multi_add(self):
        manager = DootReportManagerStack()
        assert(not bool(manager._full_trace))
        manager.add_trace("test")
        manager.add_trace("test")
        manager.add_trace("test")
        assert(len(manager._full_trace) == 3)
        assert(all(isinstance(x, TraceRecord) for x in manager._full_trace))


    def test_str(self):
        manager = DootReportManagerStack()
        manager.add_trace("test")
        manager.add_trace("test")
        manager.add_trace("test")
        assert(str(manager) == "test\ntest\ntest")


    def test_custom_formatter(self):
        class SimpleFormatter:
            def __call__(self, add_trace):
                return "- {}".format(add_trace)

        manager = DootReportManagerStack([SimpleFormatter()])
        manager.add_trace("test")
        manager.add_trace("test")
        manager.add_trace("test")
        assert(str(manager) == "- test\n- test\n- test")


    def test_custom_filter(self):
        class SimpleFilter:
            def __call__(self, add_trace):
                if Report_f.TASK in add_trace.flags:
                    return str(add_trace)

        manager = DootReportManagerStack([SimpleFilter()])
        manager.add_trace("first", flags=Report_f.TASK)
        manager.add_trace("second", flags=Report_f.JOB)
        manager.add_trace("third", flags=Report_f.TASK)
        assert(str(manager) == "first\nthird")


    def test_multi_filter(self):
        class SimpleTaskFilter:
            def __call__(self, add_trace):
                if add_trace.flags in Report_f.TASK:
                    return str(add_trace)

        class SimpleActionFilter:
            def __call__(self, add_trace):
                if add_trace.flags in Report_f.ACTION:
                    return str(add_trace)

        manager = DootReportManagerStack([ SimpleTaskFilter(), SimpleActionFilter() ])
        manager.add_trace("first", flags=Report_f.TASK)
        manager.add_trace("second", flags=Report_f.JOB)
        manager.add_trace("third", flags=Report_f.ACTION)
        assert(str(manager) == "first\nthird")


    def test_combined_filter_formatter(self):
        class SimpleTaskFilter:
            def __call__(self, add_trace):
                if add_trace.flags in Report_f.TASK:
                    return str(add_trace)

        class SimpleActionFilter:
            def __call__(self, add_trace):
                if add_trace.flags in Report_f.ACTION:
                    return "- {}".format(add_trace)

        manager = DootReportManagerStack([ SimpleTaskFilter(), SimpleActionFilter() ])
        manager.add_trace("first", flags=Report_f.TASK)
        manager.add_trace("second", flags=Report_f.JOB)
        manager.add_trace("third", flags=Report_f.ACTION)
        assert(str(manager) == "first\n- third")
