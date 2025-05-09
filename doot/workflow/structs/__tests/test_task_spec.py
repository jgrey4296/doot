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

from jgdv.structs.strang import CodeReference
from jgdv.structs.chainguard import ChainGuard
import doot
import doot.errors

from ... import DootJob
from ..._interface import TaskMeta_e, Task_p
from .. import TaskSpec, TaskName

logging = logmod.root

DEFAULT_CTOR = CodeReference(doot.aliases.task[doot.constants.entrypoints.DEFAULT_TASK_CTOR_ALIAS])

class TestTaskSpec:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_raw_ctor(self):
        obj = TaskSpec(name="simple::task")
        assert(obj is not None)
        assert(obj.name is not None)

    def test_raw_with_extras(self):
        obj = TaskSpec(name="simple::task", blah="bloo")
        assert(obj.blah == "bloo")
        assert("blah" in obj.model_extra)

    def test_extras_are_independent(self):
        obj = TaskSpec(name="simple::task", blah="bloo")
        obj2 = TaskSpec(name="simple::task", blah="aweg", aweg=2)
        assert(obj.blah == "bloo")
        assert(obj2.blah == "aweg")
        assert("blah" in obj.model_extra)
        assert("blah" in obj2.model_extra)
        assert("aweg" not in obj.model_extra)
        assert("aweg" in obj2.model_extra)

    def test_build(self):
        obj = TaskSpec.build({"name":"default::default"})
        assert(isinstance(obj, TaskSpec))
        assert(obj.name[0: ]== "default")
        assert(obj.name[1:] == "default")
        assert(DEFAULT_CTOR in str(obj.ctor))
        assert(obj.version == doot.__version__)

    def test_version(self):
        obj = TaskSpec.build({"version" : "0.5", "name":"default::default"})
        assert(isinstance(obj, TaskSpec))
        assert(obj.name[0:] == "default")
        assert(obj.name[1:] == "default")
        assert(str(obj.ctor) == DEFAULT_CTOR)
        assert(obj.version == "0.5")

    def test_basic_name(self):
        obj = TaskSpec.build({"name": "agroup::atask"})
        assert(isinstance(obj, TaskSpec))
        assert(obj.name[0:] == "agroup")
        assert(obj.name[1:] == "atask")

    def test_groupless_name(self):
        with pytest.raises(ValueError):
            TaskSpec.build({"name": "atask"})

    def test_with_extra_data(self):
        obj = TaskSpec.build({"name": "agroup::atask", "blah": "bloo", "something": [1,2,3,4]})
        assert(isinstance(obj, TaskSpec))
        assert(obj.name == "agroup::atask")
        assert("blah" in obj.extra)
        assert("something" in obj.extra)

    def test_separate_group_and_task(self):
        obj = TaskSpec.build({"name": "atask", "group": "agroup"})
        assert(isinstance(obj, TaskSpec))
        assert(obj.name[0:] == "agroup")
        assert(obj.name[1:] == "atask")

    def test_disabled_spec(self):
        obj = TaskSpec.build({"name": "agroup::atask", "disabled":True})
        assert(isinstance(obj, TaskSpec))
        assert(TaskMeta_e.DISABLED in obj.meta)

    def test_sources_empty(self):
        obj = TaskSpec.build({"name": "agroup::atask"})
        assert(isinstance(obj.sources, list))
        assert(not bool(obj.sources))

    def test_sources_name(self):
        obj = TaskSpec.build({"name": "agroup::atask", "sources":["other::task"]})
        assert(isinstance(obj.sources, list))
        assert(bool(obj.sources))
        assert(obj.sources[0] == "other::task")

    def test_sources_path(self):
        obj = TaskSpec.build({"name": "agroup::atask", "sources":["a/path.txt"]})
        assert(isinstance(obj.sources, list))
        assert(bool(obj.sources))
        assert(obj.sources[0] == pl.Path("a/path.txt"))

    def test_sources_multi(self):
        obj = TaskSpec.build({"name": "agroup::atask", "sources":["a/path.txt", "other::task"]})
        assert(isinstance(obj.sources, list))
        assert(bool(obj.sources))
        assert(obj.sources[0] == pl.Path("a/path.txt"))
        assert(obj.sources[1] == "other::task")

class TestTaskSpecValidation:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_meta_build(self):
        obj = TaskSpec.build({"name":"simple::test"})
        assert(obj.meta == {TaskMeta_e.default})
        assert(obj.meta  == {TaskMeta_e.TASK})

    def test_meta_build_multi(self):
        obj = TaskSpec.build({"name":"simple::test", "meta": ["TASK", "JOB"]})
        assert(obj.meta == {TaskMeta_e.default, TaskMeta_e.JOB})

    def test_toml_key_modification(self):
        obj = TaskSpec.build({"name":"simple::test", "blah": {}})
        assert("blah" in obj.model_fields_set)

    def test_sources_fail_if_partial(self):
        with pytest.raises(ValueError):
            TaskSpec.build({"name":"simple::test", "sources": ["basic::some.other..<partial>"]})

class TestTaskSpec_Joining:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_over(self):
        under_task = TaskSpec.build({"name": "agroup::base", "a": 0, "actions" : [{"do":"log", "msg":"blah"}]})
        over_task  = TaskSpec.build({"name": "agroup::base.a", "b": 2, "sources": ["agroup::base"]})

        match over_task.over(under_task):
            case TaskSpec() as new_spec:
                assert(new_spec is not under_task)
                assert(new_spec is not over_task)
                assert(new_spec.name != under_task.name)
                assert(over_task.name < new_spec.name)
                assert("a" in new_spec.extra)
                assert("b" in new_spec.extra)
                assert(bool(new_spec.actions))
                assert(new_spec.sources == ["agroup::base", "agroup::base.a"])
            case x:
                 assert(False), x

    def test_over_suffix(self):
        under_task = TaskSpec.build({"name": "agroup::base", "a": 0, "actions" : [{"do":"log", "msg":"blah"}]})
        over_task  = TaskSpec.build({"name": "agroup::base.a", "b": 2, "sources": "agroup::base"})

        match over_task.over(under_task, suffix="blah"):
            case TaskSpec() as new_spec:
                assert(new_spec.name == "agroup::base.a..blah")
            case x:
                 assert(False), x

    def test_over_false_suffix(self):
        under_task = TaskSpec.build({"name": "agroup::base", "a": 0, "actions" : [{"do":"log", "msg":"blah"}]})
        over_task  = TaskSpec.build({"name": "agroup::base.a", "b": 2, "sources": "agroup::base"})

        match over_task.over(under_task, suffix=False):
            case TaskSpec() as new_spec:
                assert(new_spec.name == "agroup::base.a")
            case x:
                 assert(False), x

    def test_under(self):
        under_task = TaskSpec.build({"name": "agroup::base", "a": 0, "actions" : [{"do":"log", "msg":"blah"}]})
        over_task  = TaskSpec.build({"name": "agroup::base.a", "b": 2, "sources": "agroup::base"})

        match under_task.under(over_task):
            case TaskSpec() as new_spec:
                assert(new_spec is not under_task)
                assert(new_spec is not over_task)
                assert(new_spec.name != under_task.name)
                assert(over_task.name < new_spec.name)
                assert("a" in new_spec.extra)
                assert("b" in new_spec.extra)
                assert(bool(new_spec.actions))
                assert(new_spec.sources == ["agroup::base", "agroup::base.a"])
            case x:
                 assert(False), x

    def test_under_suffix(self):
        under_task = TaskSpec.build({"name": "agroup::base", "a": 0, "actions" : [{"do":"log", "msg":"blah"}]})
        over_task  = TaskSpec.build({"name": "agroup::base.a", "b": 2, "sources": "agroup::base"})

        match under_task.under(over_task, suffix="blah"):
            case TaskSpec() as new_spec:
                assert(new_spec.name == "agroup::base.a..blah")
            case x:
                 assert(False), x

    def test_under_dict(self):
        under_task = TaskSpec.build({"name": "agroup::base", "a": 0, "actions" : [{"do":"log", "msg":"blah"}]})
        over_data = {"blah": "bloo"}

        match under_task.under(over_data):
            case TaskSpec() as new_spec:
                assert(new_spec is not under_task)
                assert(new_spec.name != under_task.name)
                assert(under_task.name < new_spec.name)
                assert("a" in new_spec.extra)
                assert(bool(new_spec.actions))
                assert("blah" in new_spec.extra)
                assert(new_spec.sources == ["agroup::base", "agroup::base..<data>"])
            case x:
                 assert(False), x

    def test_under_dict_suffix(self):
        under_task = TaskSpec.build({"name": "agroup::base", "a": 0, "actions" : [{"do":"log", "msg":"blah"}]})
        over_data = {"blah": "bloo"}

        match under_task.under(over_data, suffix="blah"):
            case TaskSpec() as new_spec:
                assert(new_spec.name == "agroup::base..<data>..blah")
            case x:
                 assert(False), x

    def test_reify_partial(self):
        base      = TaskSpec.build({"name": "agroup::base", "a": 0, "actions"    : [{"do":"log", "msg":"blah"}]})
        partial   = TaskSpec.build({"name": "agroup::base.blah..<partial>", "a": 20, "b": "blah", "sources": ["agroup::base"]})

        match partial.reify_partial(base):
            case TaskSpec() as new_spec:
                assert(new_spec.name == "agroup::base.blah")
            case x:
                 assert(False), x


    def test_reify_incorrect(self):
        bad_base      = TaskSpec.build({"name": "agroup::base.bad", "a": 0, "actions"    : [{"do":"log", "msg":"blah"}]})
        partial   = TaskSpec.build({"name": "agroup::base.blah..<partial>", "a": 20, "b": "blah", "sources": ["agroup::base"]})

        with pytest.raises(ValueError):
            partial.reify_partial(bad_base)

class TestTaskSpecInstantiation:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_instantiation(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0})
        override_task = TaskSpec.build({"name": "agroup::base.a", "b": 2, "sources": "agroup::base"})

        instance = override_task.over(base_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(instance.name != base_task.name)
        assert(override_task.name < instance.name)
        assert("a" in instance.extra)
        assert("b" in instance.extra)
        assert(instance.sources == ["agroup::base", "agroup::base.a"])

    def test_instantiation_extends_sources(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0})
        override_task = TaskSpec.build({"name": "agroup::base.a", "b": 2, "sources":[ "agroup::base"]})
        instance = override_task.over(base_task)
        assert(instance.sources == ["agroup::base", "agroup::base.a"])

    def test_instantiation_prefers_newer_extra_vals(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0})
        override_task = TaskSpec.build({"name": "agroup::base.a", "a": 100, "b": 2, "sources":[ "agroup::base"]})
        instance = override_task.over(base_task)
        assert(instance.extra['a'] == 100)
        assert(instance.sources == ["agroup::base", "agroup::base.a"])

    def test_specialize_from_fail_unrelated(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0})
        override_task = TaskSpec.build({"name": "agroup::not.base", "b": 2, "sources":["agroup::not.base"]})

        assert(not base_task.name < TaskName(override_task.sources[-1]))
        with pytest.raises(doot.errors.TrackingError):
            base_task.under(override_task)

    def test_specialize_keeps_base_actions(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0, "actions":[{"do":"basic"}]})
        override_task = TaskSpec.build({"name": "agroup::base.a", "b": 2, "sources":["agroup::base"]})

        instance = base_task.under(override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(bool(instance.actions))

    def test_specialize_keeps_override_actions(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0})
        override_task = TaskSpec.build({"name": "agroup::base.a", "b": 2, "actions":[{"do":"basic"}], "sources":["agroup::base"]})

        instance = base_task.under(override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(bool(instance.actions))

    def test_specialize_source_as_taskname(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0})
        override_task = TaskSpec.build({"name": "agroup::base.a", "b": 2, "sources" :[ "agroup::base"]})

        instance = base_task.under(override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(not isinstance(instance.ctor, TaskName))
        assert(instance.ctor == base_task.ctor)

    def test_dependency_merge(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0, "depends_on": ["basic::dep"]})
        override_task = TaskSpec.build({"name": "agroup::base.a", "depends_on": ["extra::dep"], "b": 2, "sources" :[ "agroup::base"]})

        instance = base_task.under(override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(len(instance.depends_on) == 2)

    def test_simple_data_extension(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0, "c": "blah"})
        data = {"a": 2, "b": 3}
        instance = base_task.under(data)
        assert(instance is not base_task)
        assert(base_task.name < instance.name)
        assert(instance.a == 2)
        assert(instance.b == 3)
        assert(instance.c == "blah")

    def test_sources_independece(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0, "c": "blah"})
        second = TaskSpec.build(dict(base_task))
        assert(base_task.sources is not second.sources)
        second.sources.append("blah")
        assert("blah" not in base_task.sources)

    def test_dict_sources_independence(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0, "c": "blah"})
        instance = base_task.under({})
        assert(base_task.sources is not instance.sources)
        instance.sources.append("blah")
        assert("blah" not in base_task.sources)

    def test_self_sources_independence(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0, "c": "blah"})
        with pytest.raises(doot.errors.TrackingError):
            base_task.under(base_task)

    def test_cli_arg_application(self, mocker):
        """
        With appropriate value in doot.args.tasks[name],
        the spec uses that
        """
        data = {"sub":{"agroup::base": {"blah":"bloo"}}}
        mocker.patch("doot.args", ChainGuard(data))
        base     = TaskSpec.build({"name":"agroup::base",
                                           "cli" : [{"name":"blah", "default":"aweg", "type":"str"}],
                                           })
        instance = base.under({})
        assert(not hasattr(instance, "blah"))
        match instance.make():
            case Task_p() as task:
                assert(task.state['blah'] == "bloo")
            case x:
                 assert(False), x

    def test_cli_arg_fallback_to_default(self, mocker):
        """
        Missing a value in doot.args.tasks[name],
        the spec uses the default
        """
        data = {"sub":{"agroup::base": {}}}
        mocker.patch("doot.args", ChainGuard(data))
        base     = TaskSpec.build({"name":"agroup::base",
                                           "cli" : [{"name":"blah", "default":"aweg", "type":"str"}],
                                           })
        instance = base.under({})
        assert(not hasattr(instance, "blah"))
        match instance.make():
            case Task_p() as task:
                assert(task.state['blah'] == "aweg")
            case x:
                 assert(False), x


    def test_cli_arg_override(self, mocker):
        """
        When a value is already provided for a cli arg,
        (ie: through injection)
        the spec does not override it
        """
        data = {"sub":{"agroup::base": {}}}
        mocker.patch("doot.args", ChainGuard(data))
        base     = TaskSpec.build({"name":"agroup::base",
                                           "cli" : [{"name":"blah", "default":"aweg", "type":"str"}],
                                           })
        instance = base.under({})
        other_inst = instance.make()
        other_inst.state["blah"] = "qqqq"
        assert(not hasattr(instance, "blah"))
        match instance.make(parent=other_inst):
            case Task_p() as task:
                assert(task.state['blah'] == "qqqq")
            case x:
                 assert(False), x

class TestTaskGeneration:
    """ eg: job heads and cleanup tasks

    """

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0})
        assert(isinstance(base_task, TaskSpec))

    def test_empty_cleanup_gen(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0})
        match base_task.gen_cleanup_task():
            case [cleanup_task]:
                assert(isinstance(cleanup_task, TaskSpec))
                assert(not bool(cleanup_task.actions))
                assert(base_task.name in cleanup_task.depends_on[0])
            case _:
                assert(False)

    def test_cleanup_gen(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0, "cleanup": [{"do":"log", "msg":"blah"}]})
        match base_task.gen_cleanup_task():
            case [cleanup_task]:
                assert(isinstance(cleanup_task, TaskSpec))
                assert(bool(cleanup_task.actions))
                assert(base_task.name in cleanup_task.depends_on[0])
            case _:
                assert(False)

    def test_instantiated_cleanup_gen(self):
        base_task     = TaskSpec.build({"name": "agroup::base", "a": 0, "cleanup": [{"do":"log", "msg":"blah"}]})
        match base_task.gen_cleanup_task():
            case [cleanup_task]:
                assert(isinstance(cleanup_task, TaskSpec))
                assert(bool(cleanup_task.actions))
                assert(base_task.name in cleanup_task.depends_on[0])
            case _:
                assert(False)

    def test_job_head_gen_empty_cleanup(self):
        base_task     = TaskSpec.build({"name": "agroup::+.base", "a": 0, "cleanup": []})
        match base_task.gen_job_head():
            case [TaskSpec() as head]:
               assert(TaskName.bmark_e.head in head.name)
               assert(not bool(head.actions))
               assert(base_task.name in head.depends_on[0])
            case xs:
                assert(False), xs

    def test_job_head_gen(self):
        base_task     = TaskSpec.build({"name": "agroup::+.base", "a": 0, "cleanup": [{"do":"log", "msg":"blah"}], "head_actions":[{"do":"log","msg":"bloo"}]})
        match base_task.gen_job_head():
            case [TaskSpec() as head]:
               assert(TaskName.bmark_e.head in head.name)
               assert(bool(head.actions))
               assert(base_task.name in head.depends_on[0])
            case _:
                assert(False)
