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

class TestDootTaskName:

    @pytest.fixture(scope="function")
    def setup(self):
        pass

    @pytest.fixture(scope="function")
    def cleanup(self):
        yield
        pass

    def test_complex_name(self):
        simple = structs.DootTaskName("basic", "tail")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail"])


    def test_name_with_leading_tasks(self):
        simple = structs.DootTaskName.from_str("tasks.basic::tail")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail"])

    def test_cn_with_subgroups_str(self):
        simple = structs.DootTaskName("basic.blah.bloo", "tail")
        assert(simple.head == [ "basic", "blah", "bloo"])
        assert(simple.tail == ["tail"])

    def test_cn_with_mixed_subgroups(self):
        simple = structs.DootTaskName(["basic", "blah.bloo"], "tail")
        assert(simple.head == [ "basic", "blah", "bloo"])
        assert(simple.tail == ["tail"])

    def test_cn_with_subtasks_str(self):
        simple = structs.DootTaskName("basic", "tail.blah.bloo")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail", "blah", "bloo"])

    def test_cn_with_mixed_subtasks(self):
        simple = structs.DootTaskName("basic", ["tail", "blah.bloo"])
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail", "blah", "bloo"])

    def test_cn_comparison(self):
        simple = structs.DootTaskName("basic", "tail")
        simple2 = structs.DootTaskName("basic", "tail")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_cn_comparison_fail(self):
        simple = structs.DootTaskName("basic", "tail")
        simple2 = structs.DootTaskName("basic", "bloo")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_cn_comparison_subgroups(self):
        """ where the names have subgrouping """
        simple  = structs.DootTaskName(["basic", "blah"], "tail")
        simple2 = structs.DootTaskName(["basic", "blah"], "tail")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_cn_comparison_subgroup_fail(self):
        """ where the names only differ in subgrouping """
        simple = structs.DootTaskName(["basic", "blah"], "tail")
        simple2 = structs.DootTaskName(["basic", "bloo"], "tail")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_cn_comparison_subtasks(self):
        """ where the names have subtasks"""
        simple = structs.DootTaskName(["basic", "blah"], "tail")
        simple2 = structs.DootTaskName(["basic", "blah"], "tail")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_cn_comparison_subtask_fail(self):
        """ where the names have different subtasks"""
        simple = structs.DootTaskName(["basic", "blah"], "tail")
        simple2 = structs.DootTaskName(["basic", "bloo"], "tail")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_complex_name_with_dots(self):
        simple = structs.DootTaskName("basic.blah", "tail.bloo")
        assert(simple.head == ["basic", "blah"])
        assert(simple.tail == ["tail", "bloo"])

    def test_cn_to_str(self):
        simple = structs.DootTaskName("basic", "tail")
        assert(str(simple) == "basic::tail")

    def test_cn_to_str_cmp(self):
        simple  = structs.DootTaskName("basic", "tail")
        simple2 = structs.DootTaskName("basic", "tail")
        assert(simple is not simple2)
        assert(str(simple) == str(simple2))

    def test_cn_with_subgroups(self):
        simple = structs.DootTaskName(["basic", "sub", "test"], "tail")
        assert(simple.head == ["basic", "sub", "test"])

    def test_cn_with_subgroups_str(self):
        simple = structs.DootTaskName(["basic", "sub", "test"], "tail")
        assert(str(simple) == "\"basic.sub.test\"::tail")

    def test_cn_subtask(self):
        simple = structs.DootTaskName(["basic", "sub", "test"], "tail")
        assert(str(simple) == "\"basic.sub.test\"::tail")
        sub    = simple.subtask("blah")
        assert(str(sub) == "\"basic.sub.test\"::tail.blah")

    def test_cn_subtask_with_more_groups(self):
        simple = structs.DootTaskName(["basic", "sub", "test"], "tail")
        assert(str(simple) == "\"basic.sub.test\"::tail")
        sub    = simple.subtask("blah", subgroups=["another", "subgroup"])
        assert(str(sub) == "\"basic.sub.test.another.subgroup\"::tail.blah")


    def test_lt_comparison_equal(self):
        simple = structs.DootTaskName(["basic", "sub", "test"], "tail")
        simple2 = structs.DootTaskName(["basic", "sub", "test"], "tail")
        assert(simple < simple2)


    def test_lt_comparison_fail(self):
        simple = structs.DootTaskName(["basic", "sub", "test"], "tail")
        simple2 = structs.DootTaskName(["basic", "sub", "test"], "task2")
        assert(not (simple < simple2))


    def test_lt_sub_pass(self):
        simple = structs.DootTaskName(["basic", "sub", "test"], "tail")
        simple2 = structs.DootTaskName(["basic", "sub", "test"], ["tail", "sub"])
        assert(simple < simple2)


    def test_lt_group_pass(self):
        simple = structs.DootTaskName(["basic", "sub", "test"], "tail")
        simple2 = structs.DootTaskName(["basic", "sub", "test", "another"], ["tail", "sub"])
        assert(simple < simple2)


    def test_lt_group_fail(self):
        simple = structs.DootTaskName(["basic", "sub", "test"], "tail")
        simple2 = structs.DootTaskName(["basic", "test"], ["tail", "sub"])
        assert(not (simple < simple2))




class TestDootCodeReference:
    pass
