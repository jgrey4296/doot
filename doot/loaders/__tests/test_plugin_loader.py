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
import doot
from jgdv.structs.chainguard import ChainGuard
doot._test_setup()
doot.config = ChainGuard({})
from doot.loaders import plugin_loader
logging = logmod.root

class TestPluginLoader:

    def test_initial(self):
        basic = plugin_loader.DootPluginLoader()
        assert(basic is not None)

    def test_loads_defaults(self):
        basic = plugin_loader.DootPluginLoader()
        basic.setup()
        loaded = basic.load()

        for key in (doot.constants.entrypoints.FRONTEND_PLUGIN_TYPES + doot.constants.entrypoints.BACKEND_PLUGIN_TYPES):
            assert(key in loaded), f"{key} missing"

    @pytest.mark.skip
    def test_todo(self):
        pass
