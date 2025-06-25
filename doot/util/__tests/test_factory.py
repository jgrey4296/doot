#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN201, ARG001, ANN001, ARG002, ANN202, B011, PLR2004

# Imports
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
import pathlib as pl
import warnings
# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
# ##-- end 3rd party imports

##--|
import doot
from doot.workflow import TaskSpec, TaskName
from doot.workflow._interface import Task_p, TaskSpec_i
from ..factory import SubTaskFactory, TaskFactory
##--|

# ##-- types
# isort: off
# General
import abc
import collections.abc
import typing
import types
from typing import cast, assert_type, assert_never
from typing import Generic, NewType, Never
from typing import no_type_check, final, override, overload
# Protocols and Interfaces:
from typing import Protocol, runtime_checkable
if typing.TYPE_CHECKING:
    from typing import Final, ClassVar, Any, Self
    from typing import Literal, LiteralString
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from jgdv import Maybe

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
logmod.getLogger("jgdv").propagate = False
##-- end logging

# Vars:

# Body:

class TestTaskFactory:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        match TaskFactory():
            case TaskFactory():
                assert(True)
            case x:
                assert(False), x

    def test_basic_build(self):
        obj = TaskFactory()
        match obj.build({"name":"simple::basic"}):
            case TaskSpec():
                assert(True)
            case x:
                assert(False), x

class TestTaskFactory_Over:
    """ Tests combining a TaskSpec with other data

    """

    @pytest.fixture(scope="function")
    def factory(self, mocker):
        return TaskFactory()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_over(self, factory):
        under_task = factory.build({"name": "agroup::base", "a": 0, "actions" : [{"do":"log", "msg":"blah"}]})
        over_task  = factory.build({"name": "agroup::base.a", "b": 2, "sources": ["agroup::base"]})

        match factory.merge(top=over_task, bot=under_task):
            case TaskSpec_i() as new_spec:
                assert(new_spec is not under_task)
                assert(new_spec is not over_task)
                assert(new_spec.name != under_task.name)
                assert(over_task.name < new_spec.name)
                assert("a" in new_spec.extra)
                assert("b" in new_spec.extra)
                assert(bool(new_spec.actions))
                for x in ["agroup::base", "agroup::base.a"]:
                    assert(x in new_spec.sources)
            case x:
                 assert(False), x

    def test_suffix(self, factory):
        under_task = factory.build({"name": "agroup::base", "a": 0, "actions" : [{"do":"log", "msg":"blah"}]})
        over_task  = factory.build({"name": "agroup::base.a", "b": 2, "sources": "agroup::base"})

        match factory.merge(top=over_task, bot=under_task, suffix="blah"):
            case TaskSpec() as new_spec:
                assert(new_spec.name == "agroup::base.a..blah")
            case x:
                assert(False), x

    def test_false_suffix(self, factory):
        under_task = factory.build({"name": "agroup::base", "a": 0, "actions" : [{"do":"log", "msg":"blah"}]})
        over_task  = factory.build({"name": "agroup::base.a", "b": 2, "sources": "agroup::base"})

        match factory.merge(top=over_task, bot=under_task, suffix=False):
            case TaskSpec() as new_spec:
                assert(new_spec.name == "agroup::base.a")
            case x:
                assert(False), x

    def test_extends_sources(self, factory):
        base_task                = factory.build({"name": "agroup::base", "a": 0})
        override_task            = factory.build({"name": "agroup::base.a", "b": 2, "sources":[ "agroup::base"]})
        instance                 = factory.merge(top=override_task, bot=base_task)
        for x in ["agroup::base", "agroup::base.a"]:
            assert(x in instance.sources)

    def test_prefers_newer_vals(self, factory):
        base_task                   = factory.build({"name": "agroup::base", "a": 0})
        override_task               = factory.build({"name": "agroup::base.a", "a": 100, "b": 2, "sources":[ "agroup::base"]})
        instance                    = factory.merge(top=override_task, bot=base_task)
        assert(instance.extra['a']  == 100)
        for x in  ["agroup::base", "agroup::base.a"]:
            assert(x in instance.sources)

class TestTaskFactory_Under:

    @pytest.fixture(scope="function")
    def factory(self, mocker):
        return TaskFactory()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_under(self, factory):
        under_task = factory.build({"name": "agroup::base", "a": 0, "actions" : [{"do":"log", "msg":"blah"}]})
        over_task  = factory.build({"name": "agroup::base.a", "b": 2, "sources": ["agroup::base"]})

        match factory.merge(bot=under_task, top=over_task):
            case TaskSpec() as new_spec:
                assert(new_spec is not under_task)
                assert(new_spec is not over_task)
                assert(new_spec.name != under_task.name)
                assert(over_task.name < new_spec.name)
                assert("a" in new_spec.extra)
                assert("b" in new_spec.extra)
                assert(bool(new_spec.actions))
                for x in ["agroup::base", "agroup::base.a"]:
                    assert(x in new_spec.sources)
            case x:
                 assert(False), x

    def test_suffix(self, factory):
        under_task = factory.build({"name": "agroup::base", "a": 0, "actions" : [{"do":"log", "msg":"blah"}]})
        over_task  = factory.build({"name": "agroup::base.a", "b": 2, "sources": "agroup::base"})

        match factory.merge(bot=under_task, top=over_task, suffix="blah"):
            case TaskSpec() as new_spec:
                assert(new_spec.name == "agroup::base.a..blah")
            case x:
                 assert(False), x

    def test_dict(self, factory):
        under_task = factory.build({"name": "agroup::base", "a": 0, "actions" : [{"do":"log", "msg":"blah"}]})
        over_data = {"blah": "bloo"}

        match factory.merge(bot=under_task, top=over_data):
            case TaskSpec() as new_spec:
                assert(new_spec is not under_task)
                assert(new_spec.name != under_task.name)
                assert(under_task.name < new_spec.name)
                assert("a" in new_spec.extra)
                assert(bool(new_spec.actions))
                assert("blah" in new_spec.extra)
                assert(new_spec.sources == ["agroup::base"])
            case x:
                 assert(False), x

    def test_dict_suffix(self, factory):
        under_task = factory.build({"name": "agroup::base", "a": 0, "actions" : [{"do":"log", "msg":"blah"}]})
        over_data = {"blah": "bloo"}

        match factory.merge(bot=under_task, top=over_data, suffix="blah"):
            case TaskSpec() as new_spec:
                assert(new_spec.name == "agroup::base..blah")
            case x:
                 assert(False), x

    def test_fails_from_when_unrelated(self, factory):
        """ Trying to apply base merge an unrelated task errors """
        base_task     = factory.build({"name": "agroup::base", "a": 0})
        override_task = factory.build({"name": "agroup::not.base", "b": 2, "sources":["agroup::not.base"]})

        assert(not base_task.name < TaskName(override_task.sources[-1]))
        with pytest.raises(doot.errors.TrackingError):
            factory.merge(bot=base_task, top=override_task)

    def test_keeps_base_actions(self, factory):
        """ Applying a task merge another will use the most specific set of actions """
        base_task      = factory.build({"name": "agroup::base", "a": 0, "actions":[{"do":"basic"}]})
        override_task  = factory.build({"name": "agroup::base.a", "b": 2, "sources":["agroup::base"]})

        instance       = factory.merge(bot=base_task, top=override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(len(instance.actions) == 1)
        assert("DootBaseAction" in instance.actions[0].do)

    def test_merges_actions(self, factory):
        """ Applying a task merge another will use the most specific set of actions """
        base_task      = factory.build({"name": "agroup::base", "a": 0,
                                        "actions":[{"do":"basic"}]})
        override_task  = factory.build({"name": "agroup::base.a", "b": 2,
                                        "sources":["agroup::base"],
                                        "actions": [{"do":"log", "msg":"not base action"}],
                                        })

        instance       = factory.merge(bot=base_task, top=override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(len(instance.actions) == 2)
        assert("DootBaseAction" in instance.actions[0].do)
        assert("LogAction" in instance.actions[1].do)

    def test_merges_dependencies(self, factory):
        base_task      = factory.build({"name": "agroup::base", "a": 0, "depends_on": ["basic::dep"]})
        override_task  = factory.build({"name": "agroup::base.a", "depends_on": ["extra::dep"], "b": 2, "sources"  :[ "agroup::base"]})
        instance       = factory.merge(bot=base_task, top=override_task)
        assert(instance is not base_task)
        assert(instance is not override_task)
        assert(len(instance.depends_on) == 2)

    def test_simple_data_extension(self, factory):
        base_task  = factory.build({"name": "agroup::base", "a": 0, "c": "blah"})
        data       = {"a": 2, "b": 3}
        instance   = factory.merge(bot=base_task, top=data)
        assert(instance is not base_task)
        assert(base_task.name < instance.name)
        assert(instance.a == 2)
        assert(instance.b == 3)
        assert(instance.c == "blah")

    def test_keeps_spec_independence(self, factory):
        base          = factory.build({"name": "agroup::base", "a": 0, "c": "blah"})
        second        = factory.merge(bot=base, top={})
        assert(base is not second)
        base.sources.append("testing")
        assert("testing" not in second.sources)

    def test_cant_apply_to_self(self, factory):
        base_task     = factory.build({"name": "agroup::base", "a": 0, "c": "blah"})
        with pytest.raises(doot.errors.TrackingError):
            factory.merge(bot=base_task, top=base_task)

class TestSpecFactory_Instantiation:
    """ Tests the instantiation of a spec from abstract to concrete
    and from concrete to a task
    """

    @pytest.fixture(scope="function")
    def factory(self, mocker):
        return TaskFactory()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_instantiation(self, factory):
        base_task     = factory.build({"name": "agroup::base", "a": 0})
        match factory.instantiate(base_task):
            case TaskSpec() as inst:
                assert(inst.name.uuid())
                assert(inst is not base_task)
                assert(base_task.name < inst.name)
                assert("a" in inst.extra)
            case x:
                assert(False), x

class TestTaskFactory_Make:

    @pytest.fixture(scope="function")
    def factory(self, mocker):
        return TaskFactory()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_make(self, factory):
        base      = factory.build({"name": "basic::task", "a":0})
        concrete  = factory.instantiate(base)
        assert(concrete.name.uuid())
        match factory.make(concrete):
            case Task_p() as inst:
                assert(inst.name == concrete.name)
            case x:
                 assert(False), x

class TestSubTaskFactory:
    """ Tests a spec can build related specs,
    such as it's head task (if it is a job),
    or it's cleanup task (if it is a task)

    """

    @pytest.fixture(scope="function")
    def factory(self, mocker):
        return TaskFactory()

    @pytest.fixture(scope="function")
    def subfactory(self, mocker):
        return SubTaskFactory()

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self, factory, subfactory):
        base_task = factory.build({"name": "agroup::base", "a": 0})
        assert(isinstance(base_task, TaskSpec))

    def test_abstract_spec_dont_generate_extra(self, factory, subfactory):
        base_task = factory.build({"name": "agroup::base", "a": 0})
        assert(isinstance(base_task, TaskSpec))
        match subfactory.generate_specs(base_task):
            case []:
                assert(True)
            case x:
                 assert(False), x

    def test_empty_cleanup_gen(self, factory, subfactory):
        base_spec = factory.build({"name": "agroup::base", "a": 0})
        base_task = factory.instantiate(base_spec)
        match subfactory.generate_specs(base_task):
            case [cleanup_task]:
                assert(isinstance(cleanup_task, dict))
                assert(not bool(cleanup_task['actions']))
                assert(base_task.name in cleanup_task['depends_on'][0])
            case x:
                 assert(False), x

    def test_cleanup_gen(self, factory, subfactory):
        base_spec = factory.build({"name": "agroup::base", "a": 0, "cleanup": [{"do":"log", "msg":"blah"}]})
        base_task = factory.instantiate(base_spec)
        match subfactory.generate_specs(base_task):
            case [cleanup_task]:
                assert(isinstance(cleanup_task, dict))
                assert(bool(cleanup_task['actions']))
                assert(base_task.name in cleanup_task['depends_on'][0])
            case x:
                 assert(False), x

    def test_instantiated_cleanup_gen(self, factory, subfactory):
        base_spec = factory.build({"name": "agroup::base", "a": 0, "cleanup": [{"do":"log", "msg":"blah"}]})
        base_task = factory.instantiate(base_spec)
        match subfactory.generate_specs(base_task):
            case [cleanup_task]:
                assert(isinstance(cleanup_task, dict))
                assert(bool(cleanup_task['actions']))
                assert(base_task.name in cleanup_task['depends_on'][0])
            case x:
                 assert(False), x

    def test_job_head_gen_empty_cleanup(self, factory, subfactory):
        base_spec = factory.build({"name": "agroup::+.base", "a": 0, "cleanup": []})
        base_task = factory.instantiate(base_spec)
        match subfactory.generate_specs(base_task):
            case [dict() as head]:
               assert(TaskName.Marks.head in head['name'])
               assert(not bool(head['actions']))
               assert(base_task.name in head['depends_on'][0])
            case xs:
                assert(False), xs

    def test_job_head_gen(self, factory, subfactory):
        base_spec = factory.build({"name": "agroup::+.base", "a": 0, "cleanup": [{"do":"log", "msg":"blah"}], "head_actions":[{"do":"log","msg":"bloo"}]})
        base_task = factory.instantiate(base_spec)
        match subfactory.generate_specs(base_task):
            case [dict() as head]:
               assert(TaskName.Marks.head in head['name'])
               assert(bool(head['actions']))
               assert(base_task.name in head['depends_on'][0])
            case x:
                 assert(False), x

@pytest.mark.skip
class TestTaskSpec_CLIParams:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_cli_arg_application(self, mocker):
        """
        With appropriate value in doot.args.tasks[name],
        the spec uses that
        """
        data = {"sub":{"agroup::base": {"blah":"bloo"}}}
        mocker.patch("doot.args", ChainGuard(data))
        base     = factory.build({"name":"agroup::base",
                                           "cli" : [{"name":"--blah", "default":"aweg", "type":"str"}],
                                           })
        instance = base.merge({})
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
        base     = factory.build({"name":"agroup::base",
                                           "cli" : [{"name":"blah", "default":"aweg", "type":"str"}],
                                           })
        instance = base.merge({})
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
        base     = factory.build({"name":"agroup::base",
                                           "cli" : [{"name":"-blah", "default":"aweg", "type":"str"}],
                                           })
        instance = base.merge({})
        other_inst = instance.make()
        other_inst.state["blah"] = "qqqq"
        assert(not hasattr(instance, "blah"))
        match instance.make(parent=other_inst):
            case Task_p() as task:
                assert(task.state['blah'] == "qqqq")
            case x:
                 assert(False), x
