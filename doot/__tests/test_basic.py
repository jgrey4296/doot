#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import logging as logmod
import warnings
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
##-- end imports
logging = logmod.root

import pytest
from jgdv.structs.chainguard import ChainGuard
import doot
doot._test_setup()

class TestBasicDoot:

    def test_initial(self, mocker):
        mocker.patch.object(doot,  "config", None)
        assert(doot.config is None)
        doot._test_setup()
        assert(isinstance(doot.config, ChainGuard))


    def test_initial2(self, mocker):
        mocker.patch.object(doot,  "config", None)
        assert(doot.config is None)
        doot._test_setup()
        assert(isinstance(doot.config, ChainGuard))

    def test_overlord(self, mocker):
        mocker.patch
        from doot.control.overlord import DootOverlord


    @pytest.mark.skip
    def test_todo(self):
        pass
