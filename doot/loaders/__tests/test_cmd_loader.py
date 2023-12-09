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

import pytest
import tomlguard
import doot
from importlib.metadata import EntryPoint
doot.config = tomlguard.TomlGuard({})
from doot.loaders import cmd_loader
logging = logmod.root

class TestCmdLoader(unittest.TestCase):

    def test_initial(self):
        basic = cmd_loader.DootCommandLoader()
        assert(basic is not None)

    def test_load_basic(self):
        basic = cmd_loader.DootCommandLoader()
        basic.setup(tomlguard.TomlGuard({
            "command" : [
                EntryPoint(name="list", group="doot.command", value="doot.cmds.list_cmd:ListCmd")

        ]}))
        result = basic.load()
        assert("list" in result)

    def test_load_multi(self):
        basic = cmd_loader.DootCommandLoader()
        basic.setup(tomlguard.TomlGuard({
            "command" : [
                EntryPoint(name="list", group="doot.command", value="doot.cmds.list_cmd:ListCmd"),
                EntryPoint(name="run", group="doot.command", value="doot.cmds.run_cmd:RunCmd"),

        ]}))
        result = basic.load()
        assert("list" in result)
        assert("run" in result)

    def test_load_fail(self):
        basic = cmd_loader.DootCommandLoader()
        basic.setup(tomlguard.TomlGuard({
            "command" : [
                EntryPoint(name="bad", group="doot.command", value="doot.cmds.bad:badcmd"),

        ]}))
        with pytest.raises(doot.errors.DootPluginError):
            basic.load()
