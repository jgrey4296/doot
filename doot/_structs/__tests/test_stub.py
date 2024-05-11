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
import doot
doot._test_setup()
from doot._structs import stub
from doot._structs.task_name import TaskName

class TestTaskStub:

    def test_initial(self):
        obj = stub.TaskStub.build()
        assert(isinstance(obj, stub.TaskStub))
        assert(obj.ctor == "doot.task.base_task:DootTask")
        assert(obj['name'].default == "basic::stub")

    def test_add_field(self):
        obj = stub.TaskStub.build()
        assert("blah" not in obj)
        obj['blah'].default = "bloo"
        assert("blah" in obj)

    def test_default_keys(self):
        """ check a stub has the default components of a TaskSpec  """
        obj = stub.TaskStub.build()

        default_keys = set(stub.TaskSpec.model_fields.keys())

        default_keys -= set(stub.TaskStub.skip_parts)

        default_keys.add("name")

        default_keys.add("version")
        assert(set(obj.parts.keys()) == default_keys)

    def test_to_toml(self):
        """ check a stub has the default components of a TaskSpec  """
        obj = stub.TaskStub.build()
        as_str = obj.to_toml().split("\n")
        assert(len(as_str) > 10)

    def test_to_toml_reparse(self):
        """ check a stub has the default components of a TaskSpec  """
        obj = stub.TaskStub.build()
        as_str = obj.to_toml()
        loaded = tomlguard.read(as_str)

    @pytest.mark.xfail
    def test_toml_reparse_to_spec(self):
        """ check a stub has the default components of a TaskSpec  """
        obj    = stub.TaskStub.build()
        as_str = obj.to_toml()
        loaded = tomlguard.read(as_str)
        # FIXME: currently splits the name so its not basic::stub, but 'stub', so fails building
        spec   = stub.TaskSpec.build(loaded.tasks.basic[0])

class TestTaskStubPart:

    def test_stub_initial(self):
        obj = stub.TaskStubPart(key="test", type_="list", default=[1,2,3], comment="a simple stub part")
        assert(isinstance(obj, stub.TaskStubPart))
        assert(obj.key == "test")
        assert(obj.type_ == "list")
        assert(obj.default == [1,2,3])
        assert(obj.comment == "a simple stub part")

    def test_name_reduce(self):
        obj = stub.TaskStubPart(key="name", default=TaskName.build("blah::bloo"))
        res_s = str(obj).split("\n")
        assert(res_s[0] == "[[tasks.blah]]")
        assert(res_s[1] == f"{'name':<20} = \"bloo\"")

    def test_num_reduce(self):
        obj = stub.TaskStubPart(key="amount", default=10, type="int")
        result_str     = str(obj)
        result_tomlguard  = tomlguard.read(result_str)
        assert(result_tomlguard.amount == 10)

    def test_str_reduce_with_comment(self):
        obj = stub.TaskStubPart(key="blah", default="a test", comment="a simple comment")
        as_toml = str(obj)
        assert(as_toml == f"{'blah':<20} = \"a test\"             # <str>                # a simple comment")

    def test_stub_part_list_reduce(self):
        obj = stub.TaskStubPart(key="test", type="list", default=[1,2,3], comment="a simple stub part")
        result_str     = str(obj)
        result_tomlguard  = tomlguard.read(result_str)

        assert(result_tomlguard.test == [1,2,3])

    def test_stub_part_str_reduce(self):
        obj = stub.TaskStubPart(key="test", type="str", default="test", comment="a simple stub part")
        result_str     = str(obj)
        result_tomlguard  = tomlguard.read(result_str)
        assert(result_tomlguard.test == "test")

    def test_stub_part_bool_reduce(self):
        obj = stub.TaskStubPart(key="test", type="bool", default=False, comment="a simple stub part")
        result_str     = str(obj)
        result_tomlguard  = tomlguard.read(result_str)
        assert(result_tomlguard.test == False)
