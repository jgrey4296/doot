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
