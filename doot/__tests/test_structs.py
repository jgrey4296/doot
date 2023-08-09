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

import tomler
from doot import structs

# caplog
# mocker.patch | patch.object | patch.multiple | patch.dict | stopall | stop | spy | stub
# pytest.mark.filterwarnings
# pytest.parameterize
# pytest.skip | skipif | xfail
# with pytest.deprecated_call
# with pytest.raises
# with pytest.warns(warntype)

class TestDootStructs:

    @pytest.fixture(scope="function")
    def setup(self):
        pass

    @pytest.fixture(scope="function")
    def cleanup(self):
        yield
        pass

    def test_complex_name(self):
        simple = structs.DootTaskComplexName("basic", "task")
        assert(simple.group == [ "basic"])
        assert(simple.task == ["task"])

    def test_cn_with_subgroups_str(self):
        simple = structs.DootTaskComplexName("basic.blah.bloo", "task")
        assert(simple.group == [ "basic", "blah", "bloo"])
        assert(simple.task == ["task"])

    def test_cn_with_mixed_subgroups(self):
        simple = structs.DootTaskComplexName(["basic", "blah.bloo"], "task")
        assert(simple.group == [ "basic", "blah", "bloo"])
        assert(simple.task == ["task"])

    def test_cn_with_subtasks_str(self):
        simple = structs.DootTaskComplexName("basic", "task.blah.bloo")
        assert(simple.group == [ "basic"])
        assert(simple.task == ["task", "blah", "bloo"])

    def test_cn_with_mixed_subtasks(self):
        simple = structs.DootTaskComplexName("basic", ["task", "blah.bloo"])
        assert(simple.group == [ "basic"])
        assert(simple.task == ["task", "blah", "bloo"])

    def test_cn_comparison(self):
        simple = structs.DootTaskComplexName("basic", "task")
        simple2 = structs.DootTaskComplexName("basic", "task")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_cn_comparison_fail(self):
        simple = structs.DootTaskComplexName("basic", "task")
        simple2 = structs.DootTaskComplexName("basic", "bloo")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_cn_comparison_subgroups(self):
        """ where the names have subgrouping """
        simple  = structs.DootTaskComplexName(["basic", "blah"], "task")
        simple2 = structs.DootTaskComplexName(["basic", "blah"], "task")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_cn_comparison_subgroup_fail(self):
        """ where the names only differ in subgrouping """
        simple = structs.DootTaskComplexName(["basic", "blah"], "task")
        simple2 = structs.DootTaskComplexName(["basic", "bloo"], "task")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_cn_comparison_subtasks(self):
        """ where the names have subtasks"""
        simple = structs.DootTaskComplexName(["basic", "blah"], "task")
        simple2 = structs.DootTaskComplexName(["basic", "blah"], "task")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_cn_comparison_subtask_fail(self):
        """ where the names have different subtasks"""
        simple = structs.DootTaskComplexName(["basic", "blah"], "task")
        simple2 = structs.DootTaskComplexName(["basic", "bloo"], "task")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_complex_name_with_dots(self):
        simple = structs.DootTaskComplexName("basic.blah", "task.bloo")
        assert(simple.group == ["basic", "blah"])
        assert(simple.task == ["task", "bloo"])

    def test_cn_to_str(self):
        simple = structs.DootTaskComplexName("basic", "task")
        assert(str(simple) == "basic::task")

    def test_cn_to_str_cmp(self):
        simple  = structs.DootTaskComplexName("basic", "task")
        simple2 = structs.DootTaskComplexName("basic", "task")
        assert(simple is not simple2)
        assert(str(simple) == str(simple2))

    def test_cn_with_subgroups(self):
        simple = structs.DootTaskComplexName(["basic", "sub", "test"], "task")
        assert(simple.group == ["basic", "sub", "test"])

    def test_cn_with_subgroups_str(self):
        simple = structs.DootTaskComplexName(["basic", "sub", "test"], "task")
        assert(str(simple) == "basic.sub.test::task")

    def test_cn_subtask(self):
        simple = structs.DootTaskComplexName(["basic", "sub", "test"], "task")
        assert(str(simple) == "basic.sub.test::task")
        sub    = simple.subtask("blah")
        assert(str(sub) == "basic.sub.test::task.blah")

    def test_cn_subtask_with_more_groups(self):
        simple = structs.DootTaskComplexName(["basic", "sub", "test"], "task")
        assert(str(simple) == "basic.sub.test::task")
        sub    = simple.subtask("blah", subgroups=["another", "subgroup"])
        assert(str(sub) == "basic.sub.test.another.subgroup::task.blah")

class TestDootTaskSpec:
    pass

class TestTaskStub:

    def test_initial(self):
        obj = structs.TaskStub(dict)
        assert(isinstance(obj, structs.TaskStub))
        assert(obj.ctor == dict)
        assert(str(obj['name'].default) == "tasks.stub::stub")

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
        loaded = tomler.read(as_str)


    def test_toml_reparse_to_spec(self):
        """ check a stub has the default components of a TaskSpec  """
        obj    = structs.TaskStub(dict)
        as_str = obj.to_toml()
        loaded = tomler.read(as_str)
        spec   = structs.DootTaskSpec.from_dict(loaded.tasks.stub[0]._table())
        breakpoint()
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
        obj = structs.TaskStubPart("name", default=structs.DootTaskComplexName.from_str("blah::bloo"))
        res_s = str(obj).split("\n")
        assert(res_s[0] == "[[blah]]")
        assert(res_s[1] == f"{'name':<20} = \"bloo\"")


    def test_num_reduce(self):
        obj = structs.TaskStubPart("amount", default=10, type="int")
        result_str     = str(obj)
        result_tomler  = tomler.read(result_str)
        assert(result_tomler.amount == 10)

    def test_str_reduce_with_comment(self):
        obj = structs.TaskStubPart("blah", default="a test", comment="a simple comment")
        as_toml = str(obj)
        assert(as_toml == f"{'blah':<20} = \"a test\"             # <str>                a simple comment")

    def test_stub_part_list_reduce(self):
        obj = structs.TaskStubPart("test", type="list", default=[1,2,3], comment="a simple stub part")
        result_str     = str(obj)
        result_tomler  = tomler.read(result_str)

        assert(result_tomler.test == [1,2,3])

    def test_stub_part_str_reduce(self):
        obj = structs.TaskStubPart("test", type="str", default="test", comment="a simple stub part")
        result_str     = str(obj)
        result_tomler  = tomler.read(result_str)
        assert(result_tomler.test == "test")
