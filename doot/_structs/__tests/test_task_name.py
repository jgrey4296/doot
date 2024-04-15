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
from doot import structs
from doot.enums import TaskFlags
from doot.task.base_task import DootTask

class TestDootTaskName:

    def test_creation(self):
        simple = structs.DootTaskName("basic", "tail")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail"])


    def test_build(self):
        simple = structs.DootTaskName.build("basic::tail")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail"])

    def test_name_with_leading_tasks(self):
        simple = structs.DootTaskName.build("tasks.basic::tail")
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


    def test_specialize_name(self):
        simple = structs.DootTaskName(["basic"], "tail")
        assert(str(simple) == "basic::tail")
        sub    = simple.specialize()
        assert(sub.group == "basic")
        assert(len(sub.tail) == 3)
        assert(sub.tail[0] == "tail")
        assert(sub.tail[1] == doot.constants.patterns.SPECIALIZED_ADD)


    def test_specialize_name_with_info(self):
        simple = structs.DootTaskName(["basic"], "tail")
        assert(str(simple) == "basic::tail")
        sub    = simple.specialize(info="blah")
        assert(sub.group == "basic")
        assert(len(sub.tail) == 4)
        assert(sub.tail[0] == "tail")
        assert(sub.tail[1] == doot.constants.patterns.SPECIALIZED_ADD)
        assert(sub.tail[2] == "blah")

    def test_subtask_0(self):
        simple = structs.DootTaskName(["basic", "sub", "test"], "tail")
        sub = simple.subtask(0)
        assert(sub.tail == ["tail", 0])
        assert(str(sub) == '"basic.sub.test"::tail.0')


    def test_subtask_1(self):
        simple = structs.DootTaskName(["basic", "sub", "test"], "tail")
        sub = simple.subtask(1)
        assert(sub.tail == ["tail", 1])
        assert(str(sub) == '"basic.sub.test"::tail.1')


    def test_internal(self):
        simple = structs.DootTaskName.build("agroup::_internal.task")
        assert(TaskFlags.INTERNAL in simple.meta)


class TestTaskNameComparison:

    def test_comparison(self):
        simple = structs.DootTaskName("basic", "tail")
        simple2 = structs.DootTaskName("basic", "tail")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_comparison_fail(self):
        simple = structs.DootTaskName("basic", "tail")
        simple2 = structs.DootTaskName("basic", "bloo")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_comparison_subgroups(self):
        """ where the names have subgrouping """
        simple  = structs.DootTaskName(["basic", "blah"], "tail")
        simple2 = structs.DootTaskName(["basic", "blah"], "tail")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_comparison_subgroup_fail(self):
        """ where the names only differ in subgrouping """
        simple = structs.DootTaskName(["basic", "blah"], "tail")
        simple2 = structs.DootTaskName(["basic", "bloo"], "tail")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_comparison_subtasks(self):
        """ where the names have subtasks"""
        simple = structs.DootTaskName(["basic", "blah"], "tail")
        simple2 = structs.DootTaskName(["basic", "blah"], "tail")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_comparison_subtask_fail(self):
        """ where the names have different subtasks"""
        simple = structs.DootTaskName(["basic", "blah"], "tail")
        simple2 = structs.DootTaskName(["basic", "bloo"], "tail")
        assert(simple is not simple2)
        assert(simple != simple2)


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

    def test_contains_basic_group(self):
        simple = structs.DootTaskName(["basic", "sub", "test"], "tail")
        assert("sub" in simple)


    def test_contains_basic_sub(self):
        simple = structs.DootTaskName(["basic", "sub", "test"], "tail")
        assert("tail" in simple)


    def test_contains_other_name(self):
        simple = structs.DootTaskName(["basic", "sub", "test"], "tail")
        sub   = structs.DootTaskName(["basic", "sub", "test"], ["tail", "sub"])
        assert(sub in simple)
