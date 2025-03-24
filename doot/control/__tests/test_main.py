#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import logging as logmod
import unittest
import warnings
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
##-- end imports
logging = logmod.root

import pytest
import sys
import doot

import doot._interface as API
from doot.control.main import DootMain

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
        mocker.patch.object(dmain, "_handle_cli_args", return_value=None)
        mocker.patch.object(dmain, "_set_cmd_instance")
        mocker.patch.object(dmain, "_parse_args")
        mocker.patch.object(dmain, "run_cmd")
        mocker.patch.object(dmain, "shutdown")

        with pytest.raises(SystemExit) as ctx:
            dmain.main()

        assert(ctx.value.code is API.ExitCodes.FRONTEND_FAIL)

class TestMainLoading:

    @pytest.mark.skip("TODO")
    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_load(self):
        dmain = DootMain()
        dmain._load()

class TestMainCLIArgParsing:

    @pytest.mark.skip("TODO")
    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

class TestMainCmdRun:

    @pytest.mark.skip("TODO")
    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

class TestMainShutdown:

    @pytest.mark.skip("TODO")
    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133
