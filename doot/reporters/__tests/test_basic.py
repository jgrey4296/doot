#!/usr/bin/env python3
"""
TEST File updated

"""
# ruff: noqa: ANN201, ARG001, ANN001, ARG002, ANN202, B011

# Imports
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
import pathlib as pl
import warnings
# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
# ##-- end 3rd party imports

##--|
from .. import BasicReporter, ReportFormatter
from .. import basic
from .. import _interface as API
##--|

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
LOGGER_NAME : Final[str] = "doot.test.printer"
# Body:

class TestBasicReporter:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        match BasicReporter():
            case API.Reporter_p() as x:
                assert(isinstance(x, API.Reporter_p))
            case x:
                assert(False), x

    def test_log(self, caplog):
        logger = logmod.getLogger("simple")
        with caplog.at_level(logmod.DEBUG):
            rep = BasicReporter(logger=logger)
            rep.active_level(logmod.DEBUG)
            rep.log.info("blah")

        assert("blah" in caplog.text)

    def test_context_manager(self, caplog):
        logger = logmod.getLogger("simple")
        rep = BasicReporter(logger=logger)
        with caplog.at_level(logmod.DEBUG):
            with rep:
                rep.active_level(logmod.DEBUG)
                rep.log.info("blah")

        assert("blah" in caplog.text)

    ##--|

    @pytest.mark.skip
    def test_todo(self):
        pass

class TestReporterGroup_Tree:

    @pytest.fixture(scope="function")
    def group(self, mocker):
        fmt     = ReportFormatter(segments=API.TRACE_LINES_ASCII)
        log = logmod.getLogger(LOGGER_NAME)
        return basic.TreeGroup(log=log, fmt=fmt)

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_custom_tree(self, group, caplog):
        data = [
            "First",
            "Second",
            ("Third", ["a", "b", "c"]),
            ("Fourth", ["d", "e", "f"]),
            "Fifth",
        ]

        group.tree(data)

        assert("T" in caplog.messages[0])
        assert("|   ::  [Leaf]  : First" in caplog.messages[1])
        assert("|   ::  [Leaf]  : Second" in caplog.messages[2])
        assert("|->=[" in caplog.messages[3])
        assert("|...Y   [Branch] : Third" in caplog.messages[4])
        assert(":   |   ::  [Leaf]  : a" in caplog.messages[5])
        assert(":   |   ::  [Leaf]  : b" in caplog.messages[6])
        assert(":   |   ::  [Leaf]  : c" in caplog.messages[7])
        assert(":   ⟘" in caplog.messages[8])
        assert("|->=[" in caplog.messages[9])
        assert("|...Y   [Branch] : Fourth" in caplog.messages[10])
        assert(":   |   ::  [Leaf]  : d" in caplog.messages[11])
        assert(":   |   ::  [Leaf]  : e" in caplog.messages[12])
        assert(":   |   ::  [Leaf]  : f" in caplog.messages[13])
        assert(":   ⟘" in caplog.messages[14])
        assert("|   ::  [Leaf]  : Fifth" in caplog.messages[15])
        assert("⟘" in caplog.messages[16])

    def test_nested_tree(self, group, caplog):
        data = [
            "First",
            ("Middle", ["a", ("Nested", ["b", "c"]), "d"]),
            "Last",
        ]

        group.tree(data)

        assert("T" in caplog.messages[0])
        assert("|   ::  [Leaf]  : First" in caplog.messages[1])
        assert("|->=[" in caplog.messages[2])
        assert("|...Y   [Branch] : Middle" in caplog.messages[3])
        assert(":   |   ::  [Leaf]  : a" in caplog.messages[4])
        assert(":   |->=[" in caplog.messages[5])
        assert(":   |...Y   [Branch] : Nested" in caplog.messages[6])
        assert(":   :   |   ::  [Leaf]  : b" in caplog.messages[7])
        assert(":   :   |   ::  [Leaf]  : c" in caplog.messages[8])
        assert(":   :   ⟘" in caplog.messages[9])
        assert(":   |   ::  [Leaf]  : d" in caplog.messages[10])
        assert(":   ⟘" in caplog.messages[11])
        assert("|   ::  [Leaf]  : Last" in caplog.messages[12])
        assert("⟘" in caplog.messages[13])

    def test_tree_dict(self, group, caplog):
        data = [
            "First",
            {"Middle" : ["a", {"Nested": ["b", "c"]}, "d"]},
            "Last",
        ]

        group.tree(data)

        assert("T" in caplog.text)
        assert("|   ::  [Leaf]  : First" in caplog.text)
        assert("|->=[" in caplog.text)
        assert("|...Y   [Branch] : Middle" in caplog.text)
        assert(":   |   ::  [Leaf]  : a" in caplog.text)
        assert(":   |->=[" in caplog.text)
        assert(":   |...Y   [Branch] : Nested" in caplog.text)
        assert(":   :   |   ::  [Leaf]  : b" in caplog.text)
        assert(":   :   |   ::  [Leaf]  : c" in caplog.text)
        assert(":   :   ⟘" in caplog.text)
        assert(":   |   ::  [Leaf]  : d" in caplog.text)
        assert("|   ::  [Leaf]  : Last" in caplog.text)
        assert("⟘" in caplog.text)

class TestReporterGroup_Workflow:

    @pytest.fixture(scope="function")
    def group(self, caplog):
        fmt     = ReportFormatter(segments=API.TRACE_LINES_ASCII)
        logger  = logmod.getLogger(LOGGER_NAME)
        return basic.WorkflowGroup(log=logger, fmt=fmt)

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_protocol(self):
        assert(isinstance(basic.WorkflowGroup, API.ReportGroup_p))

    def test_basic(self, group):
        assert(isinstance(group, API.ReportGroup_p))

    @pytest.mark.skip
    def test_root(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.root()

        assert("blah" in caplog.text)

    @pytest.mark.skip
    def test_wait(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.wait()

        assert("blah" in caplog.text)

    @pytest.mark.skip
    def test_act(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.wait()

        assert("blah" in caplog.text)

    @pytest.mark.skip
    def test_branch(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.wait()

        assert("blah" in caplog.text)

    @pytest.mark.skip
    def test_resume(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.wait()

        assert("blah" in caplog.text)

    @pytest.mark.skip
    def test_pause(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.wait()

        assert("blah" in caplog.text)

    @pytest.mark.skip
    def test_result(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.wait()

        assert("blah" in caplog.text)

    @pytest.mark.skip
    def test_fail(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.wait()

        assert("blah" in caplog.text)

    @pytest.mark.skip
    def test_finished(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.wait()

        assert("blah" in caplog.text)

    @pytest.mark.skip
    def test_queue(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.wait()

        assert("blah" in caplog.text)

    @pytest.mark.skip
    def test_state_result(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.wait()

        assert("blah" in caplog.text)

    @pytest.mark.skip
    def test_line(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.wait()

        assert("blah" in caplog.text)

class TestReporterGroup_General:

    @pytest.fixture(scope="function")
    def group(self, caplog):
        fmt = ReportFormatter(segments=API.TRACE_LINES_ASCII)
        logger = logmod.getLogger(LOGGER_NAME)
        return basic.GenGroup(log=logger, fmt=fmt)

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_protocol(self):
        assert(isinstance(basic.GenGroup, API.ReportGroup_p))

    def test_basic(self, group):
        assert(isinstance(group, API.ReportGroup_p))

    def test_message(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group._log.debug("blah")

        assert("blah" in caplog.text)

    def test_header(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.header()

        assert(len(set(caplog.messages)) == 2)
        assert("----  Doot  ----" in caplog.text)

    def test_line(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.line()
            group.line()

        assert(len(set(caplog.messages)) == 1)
        assert("--------" in caplog.text)

    @pytest.mark.skip
    def test_gap(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.line()
            group.line()

        assert(len(set(caplog.messages)) == 1)
        assert("--------" in caplog.text)

    @pytest.mark.skip
    def test_user(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.user

        assert(len(set(caplog.messages)) == 1)
        assert("--------" in caplog.text)

    @pytest.mark.skip
    def test_trace(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.user

        assert(len(set(caplog.messages)) == 1)
        assert("--------" in caplog.text)

    @pytest.mark.skip
    def test_failure(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.user

        assert(len(set(caplog.messages)) == 1)
        assert("--------" in caplog.text)

    @pytest.mark.skip
    def test_detail(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.user

        assert(len(set(caplog.messages)) == 1)
        assert("--------" in caplog.text)

    @pytest.mark.skip
    def test_warn(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.user

        assert(len(set(caplog.messages)) == 1)
        assert("--------" in caplog.text)

    @pytest.mark.skip
    def test_error(self, group, caplog):
        with caplog.at_level(logmod.DEBUG):
            group.user

        assert(len(set(caplog.messages)) == 1)
        assert("--------" in caplog.text)
