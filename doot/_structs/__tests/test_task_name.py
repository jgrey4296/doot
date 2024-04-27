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

from uuid import UUID
import pytest
logging = logmod.root

import tomlguard
import doot
doot._test_setup()

from doot._structs.task_name import DootTaskName
from doot.enums import TaskFlags
from doot.task.base_task import DootTask

class TestDootTaskName:

    def test_creation(self):
        simple = DootTaskName.build("basic::tail")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail"])

    def test_build(self):
        simple = DootTaskName.build("basic::tail")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail"])

    def test_name_with_leading_tasks(self):
        simple = DootTaskName.build("tasks.basic::tail")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail"])

    def test_subgroups(self):
        simple = DootTaskName.build("basic.blah.bloo::tail")
        assert(simple.head == [ "basic", "blah", "bloo"])
        assert(simple.tail == ["tail"])

    def test_mixed_subgroups(self):
        simple = DootTaskName.build('basic."blah.bloo"::tail')
        assert(simple.head == [ "basic", "blah", "bloo"])
        assert(simple.tail == ["tail"])

    def test_subtasks_str(self):
        simple = DootTaskName.build("basic::tail.blah.bloo")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail", "blah", "bloo"])

    def test_mixed_subtasks(self):
        simple = DootTaskName.build("basic::tail.blah.bloo")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail", "blah", "bloo"])

    def test_with_dots(self):
        simple = DootTaskName.build("basic.blah::tail.bloo")
        assert(simple.head == ["basic", "blah"])
        assert(simple.tail == ["tail", "bloo"])

    def test_name_to_str(self):
        simple = DootTaskName.build("basic::tail")
        assert(str(simple) == "basic::tail")

    def test_subgroups_str(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        assert(str(simple) == "\"basic.sub.test\"::tail")

    def test_internal(self):
        simple = DootTaskName.build("agroup::_internal.task")
        assert(TaskFlags.INTERNAL in simple.meta)

    def test_root_is_self(self):
        simple = DootTaskName.build("agroup::internal.task")
        assert(simple.root() == simple)

class TestTaskNameComparison:

    def test_to_str_eq(self):
        simple  = DootTaskName.build("basic::tail")
        simple2 = DootTaskName.build("basic::tail")
        assert(simple is not simple2)
        assert(str(simple) == str(simple2))

    def test_eq(self):
        simple = DootTaskName.build("basic::tail")
        simple2 = DootTaskName.build("basic::tail")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_eq_fail(self):
        simple = DootTaskName.build("basic::tail")
        simple2 = DootTaskName.build("basic::bloo")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_eq_subgroups(self):
        """ where the names have subgrouping """
        simple  = DootTaskName.build("basic.blah::tail")
        simple2 = DootTaskName.build("basic.blah::tail")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_comparison_subgroup_fail(self):
        """ where the names only differ in subgrouping """
        simple = DootTaskName.build("basic.blah::tail")
        simple2 = DootTaskName.build("basic.bloo::tail")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_comparison_subtasks(self):
        """ where the names have subtasks"""
        simple = DootTaskName.build("basic.blah::tail")
        simple2 = DootTaskName.build("basic.blah::tail")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_comparison_subtask_fail(self):
        """ where the names have different subtasks"""
        simple = DootTaskName.build("basic.blah::tail")
        simple2 = DootTaskName.build("basic.bloo::tail")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_lt_comparison_equal_fail(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        simple2 = DootTaskName.build("basic.sub.test::tail")
        assert(not simple < simple2)

    def test_lt_comparison_fail(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        simple2 = DootTaskName.build("basic.sub.test::task2")
        assert(not (simple < simple2))

    def test_lt_subtask(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        simple2 = DootTaskName.build("basic.sub.test::tail.sub")
        assert(simple < simple2)

    def test_lt_groups_must_match(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        simple2 = DootTaskName.build("basic.sub.test.another::tail.sub")
        assert(not (simple < simple2))

    def test_lt_group_fail(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        simple2 = DootTaskName.build("basic.test::tail")
        assert(not (simple < simple2))

    def test_le_comparison_equal(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        simple2 = DootTaskName.build("basic.sub.test::tail")
        assert(simple <= simple2)

    def test_contains_basic_group(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        assert("sub" in simple)

    def test_contains_basic_sub(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        assert("tail" in simple)

    def test_contains_other_name(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        sub   = DootTaskName.build("basic.sub.test::tail.sub")
        assert(sub in simple)

    def test_instance_contains_base_as_str(self):
        simple = DootTaskName.build("basic::simple.task")
        instance = simple.instantiate()
        assert(str(simple) in instance)
        assert( simple < instance )

    def test_instance_contains_base_as_taskname(self):
        simple = DootTaskName.build("basic::simple.task")
        instance = simple.instantiate()
        assert(instance in simple)
        assert(simple < instance)

    def test_base_doesnt_contain_instance(self):
        simple = DootTaskName.build("basic::simple.task")
        instance = simple.instantiate()
        assert(simple not in instance)
        assert(simple < instance)

    def test_instance_lt_simple(self):
        simple = DootTaskName.build("basic::simple.task")
        instance = simple.instantiate()
        assert(simple < instance)

    def test_instance_le_simple(self):
        simple = DootTaskName.build("basic::simple.task")
        instance = simple.instantiate()
        assert(simple <= instance)

    def test_simple_not_le_instance(self):
        simple = DootTaskName.build("basic::simple.task")
        instance = simple.instantiate()
        assert(not (instance <= simple))

class TestTaskNameExtension:

    def test_subtask(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        assert(str(simple) == "\"basic.sub.test\"::tail")
        sub    = simple.subtask("blah")
        assert(str(sub) == "\"basic.sub.test\"::tail.blah")

    @pytest.mark.xfail
    def test_subtask_root(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        sub    = simple.subtask("blah")
        assert(sub.root() == simple)

    @pytest.mark.xfail
    def test_subtask_root_from_str(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        sub    = simple.subtask("blah")
        sub_from_str = DootTaskName.build("basic.sub.test::tail.blah")
        assert(sub.root() == simple)
        assert(sub == sub_from_str)
        assert(sub_from_str.root() == simple)

    def test_subtask_with_more_groups(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        assert(str(simple) == "\"basic.sub.test\"::tail")
        sub    = simple.subtask("blah", subgroups=["another", "subgroup"])
        assert(str(sub) == "\"basic.sub.test.another.subgroup\"::tail.blah")

    def test_instanitate_name(self):
        simple = DootTaskName.build("basic::tail")
        assert(str(simple) == "basic::tail")
        sub    = simple.instantiate()
        assert(sub.group == "basic")
        assert(len(sub.tail) == 3)
        assert(sub.tail[0] == "tail")
        assert(sub.tail[1] == doot.constants.patterns.SPECIALIZED_ADD)

    def test_instantiate_name_with_prefix(self):
        simple = DootTaskName.build("basic::tail")
        assert(str(simple) == "basic::tail")
        sub    = simple.instantiate(prefix="blah")
        assert("basic::tail.blah" in sub)
        assert(sub.group == "basic")
        assert(len(sub.tail) == 4)
        assert(sub.tail[0] == "tail")
        assert(sub.tail[1] == "blah")
        assert(sub.tail[2] == doot.constants.patterns.SPECIALIZED_ADD)
        assert(isinstance(sub.last(), UUID))

    def test_subtask_0(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        sub = simple.subtask(0)
        assert(sub.tail == ["tail", "0"])
        assert(str(sub) == '"basic.sub.test"::tail.0')

    def test_subtask_1(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        sub = simple.subtask(1)
        assert(sub.tail == ["tail", "1"])
        assert(str(sub) == '"basic.sub.test"::tail.1')

    def test_head(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        sub = simple.task_head()
        assert(simple < sub)
        assert(sub in simple)
        assert(sub.last() == "$head$")

    def test_head_is_idempotent(self):
        simple = DootTaskName.build("basic.sub.test::tail")
        sub = simple.task_head()
        sub2 = sub.task_head()
        assert(sub.last() == "$head$")
        assert(sub2.last() == "$head$")
        assert(sub is sub2)

class TestTaskNameStructInteraction:

    def test_add_to_dict(self):
        simple               = DootTaskName.build("agroup::_internal.task")
        adict                = {}
        adict[simple]        = 5
        assert(adict[simple] == 5)

    def test_add_to_dict_retrieval(self):
        simple               = DootTaskName.build("agroup::_internal.task")
        adict                = {}
        adict[simple]        = 5
        duplicate            = DootTaskName.build("agroup::_internal.task")
        assert(adict[duplicate] == 5)

    def test_add_to_set(self):
        simple               = DootTaskName.build("agroup::_internal.task")
        duplicate            = DootTaskName.build("agroup::_internal.task")
        the_set = {simple, duplicate}
        assert(len(the_set) == 1)
