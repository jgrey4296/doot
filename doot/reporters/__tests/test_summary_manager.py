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

from doot.reporters.summary_manager import DootReportManagerSummary
from doot.enums import ReportEnum
from doot.structs import DootTraceRecord
from doot._abstract import Reporter_i, ReportLine_i

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

class TestSummaryReporter:

    def test_initial(self):
        manager = DootReportManagerSummary()
        assert(isinstance(manager, Reporter_i))

    def test_add_basic_trace(self):
        manager = DootReportManagerSummary()
        assert(not bool(manager._full_trace))
        manager.trace("test")
        assert(bool(manager._full_trace))
        assert(isinstance(manager._full_trace[0], DootTraceRecord))

    def test_multi_add(self):
        manager = DootReportManagerSummary()
        assert(not bool(manager._full_trace))
        manager.trace("test")
        manager.trace("test")
        manager.trace("test")
        assert(len(manager._full_trace) == 3)
        assert(all(isinstance(x, DootTraceRecord) for x in manager._full_trace))

    @pytest.mark.skip("TODO")
    def test_str(self):
        manager = DootReportManagerSummary()
        manager.trace("test", flags=ReportEnum.SUCCEED | ReportEnum.TASK)
        manager.trace("test", flags=ReportEnum.FAIL    | ReportEnum.JOB)
        manager.trace("test", flags=ReportEnum.SUCCEED | ReportEnum.ACTION)
        assert(isinstance(manager) == "    - Jobs: 0/1\n    - Tasks  : 1/0\n    - Actions: 1/0")
