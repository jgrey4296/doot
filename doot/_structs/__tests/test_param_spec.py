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
import doot
doot._test_setup()
import doot.errors
from doot.structs import ParamSpec, TaskSpec

class TestParamSpec:

    def test_paramspec(self):
        example = ParamSpec.build({
            "name" : "test"
          })
        assert(isinstance(example, ParamSpec))

    def test_equal(self):
        example = ParamSpec.build({
            "name" : "test"
          })
        assert(example == "test")
        assert(example == "test=blah")
        assert(example == "-test")
        assert(example == "-test=blah")
        assert(example == "-t")
        assert(example == "-t=blah")

    def test_equal_fail(self):
        example = ParamSpec.build({
            "name" : "test"
          })
        assert(example != "atest")
        assert(example != "--test")
        assert(example != "-tw")

    def test_consume_bool(self):
        example = ParamSpec.build({
            "name" : "test",
            "type" : "bool",
          })
        assert(example == "test")
        data = {}
        example.maybe_consume(["-test"], data)
        assert('test' in data)
        assert(bool(data['test']))

    def test_consume_short_bool(self):
        example = ParamSpec.build({
            "name" : "test"
          })
        assert(example == "test")
        data = {}
        example.maybe_consume(["-t"], data)
        assert('test' in data)
        assert(bool(data['test']))

    def test_fail_on_assign_wrong_prefix(self):
        example = ParamSpec.build({
            "name" : "test"
          })
        assert(example == "test")
        with pytest.raises(doot.errors.DootParseError):
            example.maybe_consume(["-t=blah"], {})

    def test_consume_inverse_bool(self):
        example = ParamSpec.build({
            "name" : "test"
          })
        assert(example == "test")
        data = {}
        example.maybe_consume(["-no-test"], data)
        assert('test' in data)
        assert(not bool(data['test']))

    def test_consume_list(self):
        example = ParamSpec.build({
            "name" : "test",
            "type" : list,
            "default" : [],
          })
        assert(example == "test")
        data = {'test': []}
        example.maybe_consume(["-test", "bloo"], data)
        assert('test' in data)
        assert(data['test'] == ["bloo"])

    def test_consume_list_multi(self):
        example = ParamSpec.build({
            "name" : "test",
            "type" : list,
            "default" : [],
            "positional": True
          })
        assert(example == "test")
        data = {'test': []}
        example.maybe_consume(["bloo", "blah"], data)
        assert('test' in data)
        assert(data['test'] == ["bloo", "blah"])

    @pytest.mark.xfail
    def test_consume_list_multi_joined(self):
        example = ParamSpec.build({
            "name" : "test",
            "type" : list,
            "default" : [],
          })
        assert(example == "test")
        data = {'test': []}
        args = ["-test", "bloo", "-test", "blah"]
        example.maybe_consume(args, data)
        example.maybe_consume(args, data)
        assert('test' in data)
        assert(data['test'] == ["bloo", "blah"])

    @pytest.mark.xfail
    def test_consume_set_multi_joined(self):
        example = ParamSpec.build({
            "name"    : "test",
            "type"    : set,
            "default" : set(),
          })
        assert(example == "test")
        data = {'test': set()}
        example.maybe_consume(["-test", "bloo"], data)
        example.maybe_consume(["-test", "bloo"], data)
        example.maybe_consume(["-test", "blah"], data)
        assert('test' in data)
        assert(data['test'] == {"bloo", "blah"})

    def test_consume_str(self):
        example = ParamSpec.build({
            "name" : "test",
            "type" : str,
            "default" : "",
          })
        assert(example == "test")
        data = {}
        example.maybe_consume(["-test", "bloo,blah"], data)
        assert('test' in data)
        assert(data['test'] == "bloo,blah")

    def test_consume_str_multi_set_fail(self):
        example = ParamSpec.build({
            "name" : "test",
            "type" : str,
            "default" : "",
          })
        assert(example == "test")
        data = {} # <---
        example.maybe_consume(["-test", "bloo", "blah"], data)
        with pytest.raises(Exception):
            example.maybe_consume(data, "-test=aweg")

    @pytest.mark.xfail
    def test_consume_custom_value(self):
        example = ParamSpec.build({
            "name" : "test",
            "type" : lambda x: int(x) + 2,
            "default" : 5,
          })
        assert(example == "test")
        data = {} # <---
        example.maybe_consume(["-test", "2"], data)
        assert(example == "test")
        assert(data['test'] == 4)

    def test_positional(self):
        example = ParamSpec.build({
            "name" : "test",
            "type" : list,
            "default" : [1,2,3],
            "positional" : True
            })
        assert(example.positional is True)

    def test_invisible_str(self):
        example = ParamSpec.build({
            "name" : "test",
            "type" : list,
            "default" : [1,2,3],
            "invisible" : True,
            })
        assert(str(example) == "")

    def test_not_invisible_str(self):
        example = ParamSpec.build({
            "name" : "test",
            "type" : list,
            "default" : [1,2,3],
            "invisible" : False,
            })
        assert(str(example) != "")
