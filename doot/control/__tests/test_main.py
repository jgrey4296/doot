#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
import pathlib as pl
import sys
import unittest
import warnings
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot._interface as API
from doot.control.main import DootMain

# ##-- end 1st party imports

class TestDootMain:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_initial(self, mocker):
        match DootMain():
            case DootMain() as m:
                assert(True)
            case x:
                 assert(False), x

    def test_main_method(self, mocker):
        dmain       = DootMain()
        mocker.patch.object(dmain, "_load")
        mocker.patch.object(dmain, "parse_args")
        mocker.patch.object(dmain, "handle_cli_args", return_value=None)
        mocker.patch.object(dmain, "set_cmd_instance")
        mocker.patch.object(dmain, "_install_at_exit")
        mocker.patch.object(dmain, "run_cmd")
        mocker.patch.object(dmain, "shutdown")

        with pytest.raises(SystemExit) as ctx:
            dmain()

        assert(ctx.value.code is API.ExitCodes.INITIAL)

class TestMainLoading:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_load(self):
        dmain = DootMain()
        dmain._load()

class TestMainCLIArgParsing:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    @pytest.mark.skip("TODO")
    def test_todo(self):
        pass

class TestMainCmdRun:

    @pytest.mark.skip("TODO")
    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

class TestMainShutdown:

    @pytest.mark.skip("TODO")
    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133
