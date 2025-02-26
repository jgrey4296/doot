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
from unittest import mock
##-- end imports

from importlib.metadata import EntryPoint
import pytest
import doot
from jgdv.structs.chainguard import ChainGuard

from doot.loaders import cmd
logging = logmod.root

class TestCmdLoader(unittest.TestCase):

    def test_initial(self):
        basic = cmd.DootCommandLoader()
        assert(basic is not None)

    def test_load_basic(self):
        basic = cmd.DootCommandLoader()
        basic.setup(ChainGuard({
            "command" : [
                EntryPoint(name="list", group="doot.command", value="doot.cmds.list_cmd:ListCmd")

        ]}))
        result = basic.load()
        assert("list" in result)

    def test_load_multi(self):
        basic = cmd.DootCommandLoader()
        basic.setup(ChainGuard({
            "command" : [
                EntryPoint(name="list", group="doot.command", value="doot.cmds.list_cmd:ListCmd"),
                EntryPoint(name="run", group="doot.command", value="doot.cmds.run_cmd:RunCmd"),

        ]}))
        result = basic.load()
        assert("list" in result)
        assert("run" in result)

    def test_load_fail(self):
        basic = cmd.DootCommandLoader()
        basic.setup(ChainGuard({
            "command" : [
                EntryPoint(name="bad", group="doot.command", value="doot.cmds.bad:badcmd"),

        ]}))
        with pytest.raises(doot.errors.PluginLoadError):
            basic.load()


    @pytest.mark.skip
    def test_todo(self):
        pass
