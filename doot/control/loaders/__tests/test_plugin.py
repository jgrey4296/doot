#!/usr/bin/env python3
"""

"""
from __future__ import annotations

import logging as logmod
import unittest
import warnings
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
from unittest import mock

from importlib.metadata import EntryPoint
import pytest
from jgdv.structs.chainguard import ChainGuard
import doot
from doot.control.loaders import plugin
import doot.control.loaders._interface as LoaderAPI
##--|
logging = logmod.root

frontend_plugins     : Final[list]          = doot.constants.entrypoints.FRONTEND_PLUGIN_TYPES
backend_plugins      : Final[list]          = doot.constants.entrypoints.BACKEND_PLUGIN_TYPES
plugin_types         : Final[set]           = set(frontend_plugins + backend_plugins)
##--|

class TestPluginLoader:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_initial(self):
        basic = plugin.PluginLoader()
        assert(basic is not None)

    def test_loads_defaults(self):
        basic = plugin.PluginLoader()
        basic.setup()
        loaded = basic.load()

        for key in plugin_types:
            assert(key in loaded), f"{key} missing"

    def test_all_loaded_are_entrypoints(self):
        basic = plugin.PluginLoader()
        basic.setup()
        loaded = basic.load()
        for key in plugin_types:
            for value in loaded[key]:
                assert(isinstance(value, EntryPoint))

    @pytest.mark.skip
    def test_todo(self):
        pass
