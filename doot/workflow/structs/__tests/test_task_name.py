#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN202, PLR0133
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import warnings

from uuid import UUID
import pytest

import doot

from ..task_name import TaskName
from ...task import DootTask

logging = logmod.root

class TestTaskName:

    def test_sanity(self):
        assert(True is not False)

    def test_creation(self):
        simple = TaskName("basic::tail")
        assert(simple.group == "basic")
        assert(simple.body  == "tail")

    def test_name_strip_leading_tasks_from_group(self):
        simple = TaskName("tasks.basic::tail")
        assert(simple.group == "basic")
        assert(simple.body == "tail")

    def test_subgroups(self):
        simple = TaskName("basic.blah.bloo::tail")
        assert(simple.group == "basic.blah.bloo")
        assert(simple.body == "tail")

    def test_subgroups_flattened(self):
        simple = TaskName('basic."blah.bloo"::tail')
        assert(simple.group == "basic.blah.bloo")
        assert(simple.body == "tail")

    def test_subtasks_str(self):
        simple = TaskName("basic::tail.blah.bloo")
        assert(simple.group == "basic")
        assert(simple.body == "tail.blah.bloo")

    def test_subtasks_dont_flatten(self):
        simple = TaskName("basic::tail.'blah.bloo'")
        assert(simple.group == "basic")
        assert(simple.body == "tail.'blah.bloo'")

    def test_with_dots(self):
        simple = TaskName("basic.blah::tail.bloo")
        assert(simple.group == "basic.blah")
        assert(simple.body == "tail.bloo")

    def test_name_to_str(self):
        simple = TaskName("basic::tail")
        assert(simple.section(0).end == "::")
        assert(str(simple) == "basic::tail")

    def test_end(self):
        assert(TaskName.section(0).end == "::")

    def test_subgroups_str(self):
        simple = TaskName("basic.sub.test::tail")
        assert(str(simple) == "basic.sub.test::tail")


    def test_with_head(self):
        simple = TaskName("a::b.c.d[<uuid>]")
        expect = "a::b.c.d..$head$[<uuid>]"
        assert(simple.with_head()[:] == expect)


class TestTaskName_UUID:

    def test_sanity(self):
        assert(True is not False)

    def test_no_uuid(self):
        obj = TaskName("basic::a.b.c")
        assert(not obj.uuid())

    def test_uuid(self):
        obj = TaskName("basic::a.b.c").to_uniq()
        assert(obj.uuid())

    def test_different_uuids(self):
        obj = TaskName("basic::a.b.c")
        inst1 = obj.to_uniq()
        inst2 = obj.to_uniq()
        assert(inst1 is not inst2)
        assert(inst1 != inst2)
        assert(inst1.uuid() != inst2.uuid())


    def test_uuid_is_preserved(self):
        obj = TaskName("basic::a.b.c")
        inst1 = obj.to_uniq()
        inst2 = TaskName(inst1)
        assert(inst1 is not inst2)
        assert(inst1.uuid() == inst2.uuid())
        assert(inst1 == inst2)


    def test_to_head_propagates_uuid(self):
        """
        .. basic::a.b.c[<uuid1>]
        -> basic::a.b.c..$head$.<uuid1>[<uuid2>]
        """
        obj = TaskName("basic::a.b.c")
        inst1 = obj.to_uniq()
        inst2 = inst1.with_head()
        assert(inst1 is not inst2)
        assert(inst1.uuid() == inst2.uuid())
        assert(inst1 < inst2)


    def test_to_cleanup_propagates_uuid(self):
        """
        .. basic::a.b.c[<uuid1>]
        -> basic::a.b.c..$cleanup$.<uuid1>[<uuid2>]
        """
        obj = TaskName("basic::a.b.c")
        inst1 = obj.to_uniq()
        inst2 = inst1.with_cleanup()
        assert(inst1 is not inst2)
        assert(inst1.uuid() == inst2.uuid())
        assert(inst1 < inst2)


    def test_head_can_pop_to_base(self):
        """
        .. basic::a.b.c..$head$.<uuid1>[<uuid2>]
        -> basic::a.b.c[<uuid1>]
        """
        obj   = TaskName("basic::a.b.c")
        base  = obj.to_uniq()
        head  = base.with_head()
        chop  = head.pop_generated()
        assert(base is not head)
        assert(head is not chop)
        assert(base is not chop)
        assert(head.is_head())
        assert(chop.uuid() == base.uuid())
        assert(chop == base)


    def test_cleanup_can_pop_to_base(self):
        """
        .. basic::a.b.c..$head$.<uuid1>[<uuid2>]
        -> basic::a.b.c[<uuid1>]
        """
        obj      = TaskName("basic::a.b.c")
        base     = obj.to_uniq()
        cleanup  = base.with_cleanup()
        chop     = cleanup.pop_generated()
        assert(base is not cleanup)
        assert(cleanup is not chop)
        assert(base is not chop)
        assert(cleanup.is_cleanup())
        assert(chop.uuid() == base.uuid())
        assert(chop == base)

class TestTaskName_Marks:

    def test_sanity(self):
        assert(True is not False)

    def test_extend(self):
        simple = TaskName("basic::+.tail")
        assert(simple.group == "basic")
        assert(simple.body  == "+.tail")
        assert(TaskName.Marks.extend in simple)

    def test_internal(self):
        simple = TaskName("agroup::_.internal.task")
        assert(TaskName.Marks.hide in simple)

    def test_no_internal(self):
        simple = TaskName("agroup::_internal.task")
        assert(TaskName.Marks.hide not in simple)

    def test_extend_and_internal(self):
        simple = TaskName("basic::+._.tail")
        assert(simple.group == "basic" )
        assert(simple.body == "+._.tail")
        assert(TaskName.Marks.extend in simple)
        assert(TaskName.Marks.hide in simple)

    def test_partial(self):
        simple = TaskName("basic::tail.$partial$")
        assert(TaskName.Marks.partial in simple)

    def test_customised(self):
        simple = TaskName("basic::tail.$+$")
        assert(TaskName.Marks.customised in simple)
        assert(TaskName.Marks.extend not in simple)

class TestTaskName_Comparison:

    def test_sanity(self):
        assert(True is not False)

    def test_ordering_instance_and_head(self):
        name      = TaskName("simple::task")
        instance  = name.to_uniq()
        with_head = instance.with_head()
        assert(isinstance(with_head, TaskName))
        assert(instance.uuid())
        assert(with_head.uuid())
        assert(instance.uuid() == with_head.uuid())
        assert(with_head[1,-1] == TaskName.Marks.head)
        assert(name < instance)
        assert(name < with_head)
        assert(instance < with_head)


    def test_head_must_have_base(self):
        name      = TaskName("simple::task")
        with pytest.raises(ValueError):
            name.with_head()


class TestTaskName_StructInteraction:

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
        assert(sub.pop(top=True) in the_set)
