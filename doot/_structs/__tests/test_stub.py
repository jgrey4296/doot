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

import tomlguard
from doot import structs
import doot.constants

# caplog
# mocker.patch | patch.object | patch.multiple | patch.dict | stopall | stop | spy | stub
# pytest.mark.filterwarnings
# pytest.parameterize
# pytest.skip | skipif | xfail
# with pytest.deprecated_call
# with pytest.raises
# with pytest.warns(warntype)

class TestTaskStub:

    def test_initial(self):
        obj = structs.TaskStub(dict)
        assert(isinstance(obj, structs.TaskStub))
        assert(obj.ctor == dict)
        assert(str(obj['name'].default) == "stub::stub")

    def test_default_keys(self):
        """ check a stub has the default components of a TaskSpec  """
        obj = structs.TaskStub(dict)
        default_keys = set(structs.DootTaskSpec.__annotations__.keys())
        default_keys -= set(structs.TaskStub.skip_parts)
        default_keys.add("name")
        default_keys.add("version")
        assert(set(obj.parts.keys()) == default_keys)

    def test_to_toml(self):
        """ check a stub has the default components of a TaskSpec  """
        obj = structs.TaskStub(dict)
        as_str = obj.to_toml().split("\n")
        assert(len(as_str) > 10)


    def test_to_toml_reparse(self):
        """ check a stub has the default components of a TaskSpec  """
        obj = structs.TaskStub(dict)
        as_str = obj.to_toml()
        loaded = tomlguard.read(as_str)


    def test_toml_reparse_to_spec(self):
        """ check a stub has the default components of a TaskSpec  """
        obj    = structs.TaskStub()
        as_str = obj.to_toml()
        loaded = tomlguard.read(as_str)
        spec   = structs.DootTaskSpec.from_dict(loaded.tasks.stub[0])
        pass


class TestTaskStubPart:

    def test_stub_initial(self):
        obj = structs.TaskStubPart("test", type="list", default=[1,2,3], comment="a simple stub part")
        assert(isinstance(obj, structs.TaskStubPart))
        assert(obj.key == "test")
        assert(obj.type == "list")
        assert(obj.default == [1,2,3])
        assert(obj.comment == "a simple stub part")


    def test_name_reduce(self):
        obj = structs.TaskStubPart("name", default=structs.DootTaskName.from_str("blah::bloo"))
        res_s = str(obj).split("\n")
        assert(res_s[0] == "[[tasks.blah]]")
        assert(res_s[1] == f"{'name':<20} = \"bloo\"")


    def test_num_reduce(self):
        obj = structs.TaskStubPart("amount", default=10, type="int")
        result_str     = str(obj)
        result_tomlguard  = tomlguard.read(result_str)
        assert(result_tomlguard.amount == 10)

    def test_str_reduce_with_comment(self):
        obj = structs.TaskStubPart("blah", default="a test", comment="a simple comment")
        as_toml = str(obj)
        assert(as_toml == f"{'blah':<20} = \"a test\"             # <str>                a simple comment")

    def test_stub_part_list_reduce(self):
        obj = structs.TaskStubPart("test", type="list", default=[1,2,3], comment="a simple stub part")
        result_str     = str(obj)
        result_tomlguard  = tomlguard.read(result_str)

        assert(result_tomlguard.test == [1,2,3])

    def test_stub_part_str_reduce(self):
        obj = structs.TaskStubPart("test", type="str", default="test", comment="a simple stub part")
        result_str     = str(obj)
        result_tomlguard  = tomlguard.read(result_str)
        assert(result_tomlguard.test == "test")


    def test_stub_part_bool_reduce(self):
        obj = structs.TaskStubPart("test", type="bool", default=False, comment="a simple stub part")
        result_str     = str(obj)
        result_tomlguard  = tomlguard.read(result_str)
        assert(result_tomlguard.test == False)
