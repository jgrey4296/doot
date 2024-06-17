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

from doot._structs.task_name import TaskName
from doot.enums import TaskMeta_f
from doot.task.base_task import DootTask

class TestTaskName:

    def test_creation(self):
        simple = TaskName.build("basic::tail")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail"])

    def test_build(self):
        simple = TaskName.build("basic::tail")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail"])

    def test_build_job(self):
        simple = TaskName.build("basic.+::tail")
        assert(simple.head == [ "basic", "+"])
        assert(simple.tail == ["tail"])
        assert(TaskMeta_f.JOB in simple)

    def test_build_internal_job(self):
        simple = TaskName.build("basic.+::_.tail")
        assert(simple.head == [ "basic", "+"])
        assert(simple.tail == ["_", "tail"])
        assert(TaskMeta_f.JOB in simple)
        assert(TaskMeta_f.INTERNAL in simple)

    def test_internal(self):
        simple = TaskName.build("agroup::_.internal.task")
        assert(TaskMeta_f.INTERNAL in simple)

    def test_no_internal(self):
        simple = TaskName.build("agroup::_internal.task")
        assert(TaskMeta_f.INTERNAL not in simple)

    def test_name_with_leading_tasks(self):
        simple = TaskName.build("tasks.basic::tail")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail"])

    def test_subgroups(self):
        simple = TaskName.build("basic.blah.bloo::tail")
        assert(simple.head == [ "basic", "blah", "bloo"])
        assert(simple.tail == ["tail"])

    def test_mixed_subgroups(self):
        simple = TaskName.build('basic."blah.bloo"::tail')
        assert(simple.head == [ "basic", "blah", "bloo"])
        assert(simple.tail == ["tail"])

    def test_subtasks_str(self):
        simple = TaskName.build("basic::tail.blah.bloo")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail", "blah", "bloo"])

    def test_mixed_subtasks(self):
        simple = TaskName.build("basic::tail.blah.bloo")
        assert(simple.head == [ "basic"])
        assert(simple.tail == ["tail", "blah", "bloo"])

    def test_with_dots(self):
        simple = TaskName.build("basic.blah::tail.bloo")
        assert(simple.head == ["basic", "blah"])
        assert(simple.tail == ["tail", "bloo"])

    def test_name_to_str(self):
        simple = TaskName.build("basic::tail")
        assert(str(simple) == "basic::tail")

    def test_subgroups_str(self):
        simple = TaskName.build("basic.sub.test::tail")
        assert(str(simple) == "\"basic.sub.test\"::tail")

class TestTaskNameComparison:

    def test_to_str_eq(self):
        simple  = TaskName.build("basic::tail")
        simple2 = TaskName.build("basic::tail")
        assert(simple is not simple2)
        assert(str(simple) == str(simple2))

    def test_eq(self):
        simple = TaskName.build("basic::tail")
        simple2 = TaskName.build("basic::tail")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_eq_fail(self):
        simple = TaskName.build("basic::tail")
        simple2 = TaskName.build("basic::bloo")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_eq_subgroups(self):
        """ where the names have subgrouping """
        simple  = TaskName.build("basic.blah::tail")
        simple2 = TaskName.build("basic.blah::tail")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_comparison_subgroup_fail(self):
        """ where the names only differ in subgrouping """
        simple = TaskName.build("basic.blah::tail")
        simple2 = TaskName.build("basic.bloo::tail")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_comparison_subtasks(self):
        """ where the names have subtasks"""
        simple = TaskName.build("basic.blah::tail")
        simple2 = TaskName.build("basic.blah::tail")
        assert(simple is not simple2)
        assert(simple == simple2)

    def test_comparison_subtask_fail(self):
        """ where the names have different subtasks"""
        simple = TaskName.build("basic.blah::tail")
        simple2 = TaskName.build("basic.bloo::tail")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_lt_comparison_equal_fail(self):
        simple = TaskName.build("basic.sub.test::tail")
        simple2 = TaskName.build("basic.sub.test::tail")
        assert(not simple < simple2)

    def test_lt_comparison_fail(self):
        simple = TaskName.build("basic.sub.test::tail")
        simple2 = TaskName.build("basic.sub.test::task2")
        assert(not (simple < simple2))

    def test_lt_subtask(self):
        simple = TaskName.build("basic.sub.test::tail")
        simple2 = TaskName.build("basic.sub.test::tail.sub")
        assert(simple < simple2)

    def test_lt_groups_must_match(self):
        simple = TaskName.build("basic.sub.test::tail")
        simple2 = TaskName.build("basic.sub.test.another::tail.sub")
        assert(not (simple < simple2))

    def test_lt_group_fail(self):
        simple = TaskName.build("basic.sub.test::tail")
        simple2 = TaskName.build("basic.test::tail")
        assert(not (simple < simple2))

    def test_le_comparison_equal(self):
        simple = TaskName.build("basic.sub.test::tail")
        simple2 = TaskName.build("basic.sub.test::tail")
        assert(simple <= simple2)

    def test_contains_basic_group(self):
        simple = TaskName.build("basic.sub.test::tail")
        assert("sub" in simple)

    def test_contains_basic_sub(self):
        simple = TaskName.build("basic.sub.test::tail")
        assert("tail" in simple)

    def test_contains_other_name(self):
        simple = TaskName.build("basic.sub.test::tail")
        sub   = TaskName.build("basic.sub.test::tail.sub")
        assert(sub in simple)

    def test_instance_contains_base_as_str(self):
        simple = TaskName.build("basic::simple.task")
        instance = simple.instantiate()
        assert(str(simple) in instance)
        assert( simple < instance )

    def test_instance_contains_base_as_taskname(self):
        simple = TaskName.build("basic::simple.task")
        instance = simple.instantiate()
        assert(instance in simple)
        assert(simple < instance)

    def test_base_doesnt_contain_instance(self):
        simple = TaskName.build("basic::simple.task")
        instance = simple.instantiate()
        assert(simple not in instance)
        assert(simple < instance)

    def test_instance_lt_simple(self):
        simple = TaskName.build("basic::simple.task")
        instance = simple.instantiate()
        assert(simple < instance)

    def test_instance_le_simple(self):
        simple = TaskName.build("basic::simple.task")
        instance = simple.instantiate()
        assert(simple <= instance)

    def test_simple_not_le_instance(self):
        simple = TaskName.build("basic::simple.task")
        instance = simple.instantiate()
        assert(not (instance <= simple))

class TestTaskNameExtension:

    def test_subtask(self):
        simple = TaskName.build("basic.sub.test::tail")
        assert(str(simple) == "\"basic.sub.test\"::tail")
        sub    = simple.subtask("blah")
        assert(str(sub) == "\"basic.sub.test\"::tail..blah")

    def test_subtask_with_more_groups(self):
        simple = TaskName.build("basic.sub.test::tail")
        assert(str(simple) == "\"basic.sub.test\"::tail")
        sub    = simple.subtask("blah", subgroups=["another", "subgroup"])
        assert(str(sub) == "\"basic.sub.test.another.subgroup\"::tail..blah")

    def test_instanitate_name(self):
        simple = TaskName.build("basic::tail")
        assert(str(simple) == "basic::tail")
        sub    = simple.instantiate()
        assert(sub.group == "basic")
        assert(len(sub.tail) == 4)
        assert(sub.tail[0] == "tail")
        assert(sub.tail[2] == doot.constants.patterns.SPECIALIZED_ADD)

    def test_instantiate_name_twice(self):
        simple = TaskName.build("basic::tail")
        assert(str(simple) == "basic::tail")
        sub    = simple.instantiate()
        sub2   = sub.instantiate()
        assert(sub.group == "basic")
        assert(len(sub.tail) == 4)
        assert(sub.tail[0] == "tail")
        assert(sub.tail[2] == doot.constants.patterns.SPECIALIZED_ADD)
        assert(simple < sub < sub2)

    def test_instantiate_name_with_prefix(self):
        simple = TaskName.build("basic::tail")
        assert(str(simple) == "basic::tail")
        sub    = simple.instantiate(prefix="blah")
        assert("basic::tail..blah" in sub)
        assert(sub.group == "basic")
        assert(len(sub.tail) == 5)
        assert(sub.tail[0] == "tail")
        assert(sub.tail[1] == TaskName._root_marker)
        assert(sub.tail[2] == "blah")
        assert(sub.tail[3] == doot.constants.patterns.SPECIALIZED_ADD)
        assert(isinstance(sub.last(), UUID))

    def test_subtask_0(self):
        simple = TaskName.build("basic.sub.test::tail")
        sub = simple.subtask(0)
        assert(sub.tail == ["tail", TaskName._root_marker, "0"])
        assert(str(sub) == '"basic.sub.test"::tail..0')

    def test_subtask_1(self):
        simple = TaskName.build("basic.sub.test::tail")
        sub = simple.subtask(1)
        assert(sub.tail == ["tail", TaskName._root_marker, "1"])
        assert(str(sub) == '"basic.sub.test"::tail..1')

    def test_head(self):
        simple = TaskName.build("basic.sub.test::tail")
        instance = simple.instantiate()
        sub = instance.job_head()
        assert(simple < sub)
        assert(sub in simple)
        assert(sub.last() == TaskName._head_marker)

    def test_head_only_on_instances(self):
        simple             = TaskName.build("basic.sub.test::tail")
        head               = simple.job_head()
        assert(head.last() == TaskName._head_marker)

    def test_head_on_instance(self):
        simple             = TaskName.build("basic.sub.test::tail")
        instance           = simple.instantiate()
        head               = instance.job_head()
        assert(simple < instance < head)
        assert(not (simple < head < instance))
        assert(head.last() == TaskName._head_marker)

    def test_head_is_idempotent(self):
        simple             = TaskName.build("basic.sub.test::tail")
        instance           = simple.instantiate()
        sub                = instance.job_head()
        sub2               = sub.job_head()
        assert(sub.last()  == TaskName._head_marker)
        assert(sub2.last() == TaskName._head_marker)
        assert(sub is sub2)

class TestNameRoots:

    def test_add_root(self):
        simple  = TaskName.build("basic::tail")
        simple2 = TaskName.build("basic::tail.")
        added_root = simple.add_root()

        assert(simple != simple2)
        assert(added_root == simple2)
        assert(str(simple) != str(simple2))
        assert(str(added_root) == str(simple2))


    def test_has_root(self):
        simple  = TaskName.build("basic::tail")
        simple2 = TaskName.build("basic::tail..blah")
        added_root = simple.subtask("bloo")
        assert(not simple.has_root())
        assert(simple2.has_root())
        assert(added_root.has_root())


    def test_root_auto_filter(self):
        simple  = TaskName.build("basic::tail..a")
        simple2 = TaskName.build("basic::tail....a")
        assert(simple == simple2)

    def test_root_auto_filter_last(self):
        simple  = TaskName.build("basic::tail..")
        simple2 = TaskName.build("basic::tail....")
        assert(simple == simple2)

    def test_root_eq(self):
        simple  = TaskName.build("basic::tail.")
        simple2 = TaskName.build("basic::tail.")
        assert(simple is not simple2)
        assert(str(simple) == str(simple2))

    def test_root_eq_fail(self):
        simple = TaskName.build("basic::tail.")
        simple2 = TaskName.build("basic::bloo.")
        assert(simple is not simple2)
        assert(simple != simple2)

    def test_root_lt(self):
        simple = TaskName.build("basic::tail.")
        simple2 = TaskName.build("basic::tail..b.c")
        assert(simple is not simple2)
        assert(simple < simple2)

    def test_root_lt_fail(self):
        simple = TaskName.build("basic::tail.")
        simple2 = TaskName.build("basic::tail.b.c")
        assert(simple is not simple2)
        assert(not simple < simple2)

    def test_root_contains(self):
        simple = TaskName.build("basic::tail.")
        simple2 = TaskName.build("basic::tail..b.c")
        assert(simple is not simple2)
        assert(simple2 in simple)

    def test_root_contains_fail(self):
        simple = TaskName.build("basic::tail.")
        simple2 = TaskName.build("basic::tail.b.c")
        assert(simple is not simple2)
        assert(simple2 not in simple)

    def test_root_is_self(self):
        simple = TaskName.build("agroup::simple.task")
        assert(simple.root() == simple)
        assert(simple._roots == (-1, -1))

    def test_root_basic(self):
        simple = TaskName.build("agroup::simple.task..a")
        assert(simple.root() == "agroup::simple.task")
        assert(simple._roots == (2, 2))

    def test_root_subtask_preserves_marker(self):
        simple = TaskName.build("agroup::simple.task..a")
        root = simple.root()
        assert(root == "agroup::simple.task")
        assert(root.subtask("blah") == "agroup::simple.task..blah")
        assert(simple._roots == (2, 2))

    def test_root_multi(self):
        simple = TaskName.build("agroup::simple.task..a.c..d.e.f")
        assert(simple._roots == (2, 5))
        assert(simple.root() == "agroup::simple.task..a.c")
        assert(simple.root()._roots == (2, 2))

    def test_root_multi_repeat(self):
        simple = TaskName.build("agroup::simple.task..a.c..d.e.f")
        assert(simple._roots == (2, 5))
        assert(simple.root() == "agroup::simple.task..a.c")
        assert(simple.root()._roots == (2, 2))
        assert(simple.root().root() == "agroup::simple.task")
        assert(simple.root().root()._roots == (-1, -1))

    def test_root_multi_end(self):
        simple = TaskName.build("agroup::simple.task..a.c..d.e.f")
        assert(simple._roots == (2, 5))
        assert(simple.root().root().root() == simple.root().root())

    def test_root_multi_jump_to_top(self):
        simple = TaskName.build("agroup::simple.task..a.c..d.e.f")
        assert(simple.root(top=True) == "agroup::simple.task")
        assert(simple.root().root() == "agroup::simple.task")
        assert(simple.root().root().root() == simple.root(top=True))

    def test_subtask_root(self):
        simple = TaskName.build("basic.sub.test::tail")
        sub    = simple.subtask("blah")
        assert(sub.root() == simple)

    def test_subtask_root_from_str(self):
        simple = TaskName.build("basic.sub.test::tail")
        sub    = simple.subtask("blah")
        sub_from_str = TaskName.build("basic.sub.test::tail..blah")
        assert(sub.root() == simple)
        assert(sub == sub_from_str)
        assert(sub_from_str.root() == simple)

class TestTaskNameStructInteraction:

    def test_add_to_dict(self):
        simple               = TaskName.build("agroup::_.internal.task")
        adict                = {}
        adict[simple]        = 5
        assert(adict[simple] == 5)

    def test_add_to_dict_retrieval(self):
        simple               = TaskName.build("agroup::_.internal.task")
        adict                = {}
        adict[simple]        = 5
        duplicate            = TaskName.build("agroup::_.internal.task")
        assert(adict[duplicate] == 5)

    def test_add_to_set(self):
        simple               = TaskName.build("agroup::_.internal.task")
        duplicate            = TaskName.build("agroup::_.internal.task")
        the_set = {simple, duplicate}
        assert(len(the_set) == 1)
