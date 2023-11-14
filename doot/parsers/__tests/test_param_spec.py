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
import doot.errors
from doot.parsers.parser import DootArgParser
from doot.structs import DootParamSpec, DootTaskSpec

class TestParamSpec:

    def test_paramspec(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        assert(isinstance(example, DootParamSpec))

    def test_equal(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        assert(example == "test")
        assert(example == "test=blah")
        assert(example == "-test")
        assert(example == "-test=blah")
        assert(example == "-t")
        assert(example == "-t=blah")

    def test_equal_fail(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        assert(example != "atest")
        assert(example != "--test")
        assert(example != "-tw")

    def test_add_value_bool(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        assert(example == "test")
        data = {}
        example.add_value_to(data, "test")
        assert('test' in data)
        assert(bool(data['test']))

    def test_add_value_short_bool(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        assert(example == "test")
        data = {}
        example.add_value_to(data, "-t")
        assert('test' in data)
        assert(bool(data['test']))

    def test_add_value_short_bool(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        assert(example == "test")
        data = {}
        with pytest.raises(doot.errors.DootParseError):
            example.add_value_to(data, "-t=blah")

    def test_add_value_inverse_bool(self):
        example = DootParamSpec.from_dict({
            "name" : "test"
          })
        assert(example == "test")
        data = {}
        example.add_value_to(data, "-no-test")
        assert('test' in data)
        assert(not bool(data['test']))

    def test_add_value_list(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [],
          })
        assert(example == "test")
        data = {'test': []}
        example.add_value_to(data, "-test=bloo")
        assert('test' in data)
        assert(data['test'] == ["bloo"])

    def test_add_value_list_multi(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [],
          })
        assert(example == "test")
        data = {'test': []}
        example.add_value_to(data, "-test=bloo")
        example.add_value_to(data, "-test=blah")
        assert('test' in data)
        assert(data['test'] == ["bloo", "blah"])

    def test_add_value_list_multi_joined(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [],
          })
        assert(example == "test")
        data = {'test': []}
        example.add_value_to(data, "-test=bloo,blah")
        assert('test' in data)
        assert(data['test'] == ["bloo", "blah"])

    def test_add_value_set_multi_joined(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : set,
            "default" : set(),
          })
        assert(example == "test")
        data = {'test': set()}
        example.add_value_to(data, "-test=bloo,blah")
        assert('test' in data)
        assert(data['test'] == {"bloo", "blah"})

    def test_add_value_set_missing_joined(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : set,
            "default" : set(),
          })
        assert(example == "test")
        data = {} # <---
        example.add_value_to(data, "-test=bloo,blah")
        assert('test' in data)
        assert(data['test'] == {"bloo", "blah"})

    def test_add_value_str(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : str,
            "default" : "",
          })
        assert(example == "test")
        data = {} # <---
        example.add_value_to(data, "-test=bloo,blah")
        assert('test' in data)
        assert(data['test'] == "bloo,blah")

    def test_add_value_str_multi_set_fail(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : str,
            "default" : "",
          })
        assert(example == "test")
        data = {} # <---
        example.add_value_to(data, "-test=bloo,blah")
        with pytest.raises(Exception):
            example.add_value_to(data, "-test=aweg")

    def test_add_value_custom_value(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : lambda x: int(x) + 2,
            "default" : 5,
          })
        assert(example == "test")
        data = {} # <---
        example.add_value_to(data, "-test=2")
        assert(example == "test")
        assert(data['test'] == 4)

    def test_positional(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [1,2,3],
            "positional" : True
            })
        assert(example.positional is True)

    def test_invisible_str(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [1,2,3],
            "invisible" : True,
            })
        assert(str(example) == "")

    def test_not_invisible_str(self):
        example = DootParamSpec.from_dict({
            "name" : "test",
            "type" : list,
            "default" : [1,2,3],
            "invisible" : False,
            })
        assert(str(example) != "")
