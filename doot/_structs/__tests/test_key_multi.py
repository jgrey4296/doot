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

logging = logmod.root

from tomlguard import TomlGuard
import doot
doot._test_setup()
from doot.control.locations import DootLocations
from doot.structs import DootKey, DootActionSpec
from doot._structs import key as dkey

KEY_BASES               : Final[str] = ["bob", "bill", "blah", "other"]
MULTI_KEYS              : Final[str] = ["{bob}/{bill}", "{blah}/{bloo}", "{blah}/{bloo}"]
NON_PATH_MUTI_KEYS      : Final[str] = ["{bob}_{bill}", "{blah} <> {bloo}", "! {blah}! {bloo}!"]
KEY_INDIRECTS           : Final[str] = ["bob_", "bill_", "blah_", "other_"]

TEST_LOCS               : Final[DootLocations] = DootLocations(pl.Path.cwd()).update({"blah": "doot"})

class TestMultiKey:

    @pytest.mark.parametrize("key,targets", [("{blah} test", ["blah"]), ("{blah} {bloo}", ["blah", "bloo"]), ("{blah} {blah}", ["blah"])])
    def test_keys(self, key, targets):
        obj           = DootKey.build(key, strict=False)
        assert(obj.keys() == set(targets))

    @pytest.mark.parametrize("key,target", [("{blah}/bloo", "./doot/bloo"), ("{blah}/bloo/{aweg}", "./doot/bloo/qqqq") ])
    def test_to_path_expansion(self, mocker, key, target):
        mocker.patch.dict("doot.__dict__", locs=TEST_LOCS)
        obj           = DootKey.build(key, strict=False)
        spec          = mocker.Mock(params={}, spec=DootActionSpec)
        state         = {"aweg": "qqqq"}
        result        = obj.to_path(spec, state)
        assert(isinstance(result, pl.Path))
        assert(result == pl.Path(target).expanduser().resolve())

    @pytest.mark.parametrize("key,target", [("{blah}/bloo", "doot/bloo"), ("test !!! {blah}", "test !!! doot"), ("{aweg}-{blah}", "BOO-doot") ])
    def test_expansion(self, mocker, key, target):
        obj           = DootKey.build(key, strict=False)
        spec          = mocker.Mock(params={}, spec=DootActionSpec)
        state         = {"blah": "doot", "aweg": "BOO"}
        result        = obj.expand(spec, state)
        assert(isinstance(result, str))
        assert(result == target)
