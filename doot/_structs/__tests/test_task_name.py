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

import doot

from doot._structs.task_name import TaskName
from doot.task.core.task import DootTask

class TestTaskName:

    def test_sanity(self):
        assert(True is not False)

    def test_creation(self):
        simple = TaskName("basic::tail")
        assert(simple.group == [ "basic"])
        assert(simple.body() == ["tail"])


    def test_build(self):
        simple = TaskName("basic::tail")
        assert(simple.group == [ "basic"])
        assert(simple.body() == ["tail"])

    def test_build_job(self):
        simple = TaskName("basic::+.tail")
        assert(simple.group == [ "basic" ])
        assert(simple.body() == ["+", "tail"])
        assert(TaskName.bmark_e.extend in simple)

    def test_build_internal_job(self):
        simple = TaskName("basic::+._.tail")
        assert(simple.group == [ "basic"] )
        assert(simple.body() == ["+", "_", "tail"])
        assert(TaskName.bmark_e.extend in simple)
        assert(TaskName.bmark_e.hide in simple)

    def test_internal(self):
        simple = TaskName("agroup::_.internal.task")
        assert(TaskName.bmark_e.hide in simple)

    def test_no_internal(self):
        simple = TaskName("agroup::_internal.task")
        assert(TaskName.bmark_e.hide != simple[1:0])

    def test_name_strip_leading_tasks_from_group(self):
        simple = TaskName("tasks.basic::tail")
        assert(simple.group == [ "basic"])
        assert(simple.body() == ["tail"])

    def test_subgroups(self):
        simple = TaskName("basic.blah.bloo::tail")
        assert(simple.group == [ "basic", "blah", "bloo"])
        assert(simple.body() == ["tail"])

    def test_mixed_subgroups(self):
        simple = TaskName('basic."blah.bloo"::tail')
        assert(simple.group == [ "basic", "blah", "bloo"])
        assert(simple.body() == ["tail"])

    def test_subtasks_str(self):
        simple = TaskName("basic::tail.blah.bloo")
        assert(simple.group == [ "basic"])
        assert(simple.body() == ["tail", "blah", "bloo"])

    def test_mixed_subtasks(self):
        simple = TaskName("basic::tail.blah.bloo")
        assert(simple.group == [ "basic"])
        assert(simple.body() == ["tail", "blah", "bloo"])

    def test_with_dots(self):
        simple = TaskName("basic.blah::tail.bloo")
        assert(simple.group == ["basic", "blah"])
        assert(simple.body() == ["tail", "bloo"])

    def test_name_to_str(self):
        simple = TaskName("basic::tail")
        assert(simple._separator == "::")
        assert(str(simple) == "basic::tail")

    def test_subgroups_str(self):
        simple = TaskName("basic.sub.test::tail")
        assert(str(simple) == "basic.sub.test::tail")

class TestTaskNameComparison:

    def test_sanity(self):
        assert(True is not False)

    def test_ordering_instance_and_head(self):
        name      = TaskName("simple::task")
        instance  = name.to_uniq()
        with_head = instance.with_head()
        assert(isinstance(with_head, TaskName))
        assert(with_head[1:-1] == TaskName.bmark_e.head)
        assert(name < instance < with_head)

    def test_job_head_to_instance(self):
        name      = TaskName("simple::task")
        with_head = name.with_head()
        instance  = with_head.to_uniq()
        assert(isinstance(instance, TaskName))
        assert(isinstance(instance[-1], UUID))
        assert(instance.root() == name)
        assert(name < with_head < instance)

class TestTaskNameStructInteraction:

    def test_add_to_dict(self):
        simple               = TaskName("agroup::_.internal.task")
        adict                = {}
        adict[simple]        = 5
        assert(adict[simple] == 5)

    def test_add_to_dict_retrieval(self):
        simple               = TaskName("agroup::_.internal.task")
        adict                = {}
        adict[simple]        = 5
        duplicate            = TaskName("agroup::_.internal.task")
        assert(adict[duplicate] == 5)

    def test_add_to_set(self):
        simple               = TaskName("agroup::_.internal.task")
        duplicate            = TaskName("agroup::_.internal.task")
        the_set = {simple, duplicate}
        assert(len(the_set) == 1)

    def test_name_in_set(self):
        first = TaskName("agroup::_.internal.task")
        second = TaskName("other.group::task.second")
        the_set = {first, second}
        assert(len(the_set) == 2)

    def test_root_in_set(self):
        first = TaskName("agroup::_.internal.task")
        second = TaskName("other.group::task.second")
        sub    = second.push("blah")
        the_set = {first, second}
        assert(sub.root() in the_set)
