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

import doot
doot._test_setup()
from doot.actions.job_expansion import JobExpandAction, JobMatchAction
import doot.errors
from doot.structs import DKey, ActionSpec, TaskName, TaskSpec

class TestJobExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "job.expand", "args":[], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": TaskName.build("agroup::basic")}

    def test_sanity(self, spec, state):
        obj = JobExpandAction()
        assert(isinstance(obj, JobExpandAction))

    def test_empty_expansion(self, spec, state):
        obj = JobExpandAction()
        result = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(len(result['specs']) == 1)

    @pytest.mark.parametrize("count", [1,11,2,5,20])
    def test_count_expansion(self, spec, state, count):
        spec.kwargs._table()['from'] = count
        obj = JobExpandAction()
        result = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(len(result['specs']) == count)

    def test_list_expansion(self, spec, state):
        args = ["a", "b", "c"]
        spec.kwargs._table()['from'] = args
        state['inject'] = {"replace": ['target']}
        obj = JobExpandAction()
        result = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(len(result['specs']) == 3)
        for spec, expect in zip(result['specs'], args):
            assert(spec.target == expect)

    def test_action_template(self, spec, state):
        state['template'] = "test::task"
        obj = JobExpandAction()
        result = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(result['specs'][0].sources == ["test::task"])
        assert(len(result['specs'][0].actions) == 0)

    def test_taskname_template(self, spec, state):
        state['template'] = [{"do":"basic"}, {"do":"basic"}, {"do":"basic"}]
        obj = JobExpandAction()
        result = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(len(result['specs'][0].actions) == 3)


    def test_basic_expander(self, spec, state):
        state.update(dict(_task_name=TaskName.build("agroup::basic"),
                          inject={"replace":["aKey"]},
                          base="base::task"))

        state['from'] = ["first", "second", "third"]
        jqa    = JobExpandAction()
        result = jqa(spec, state)
        assert(isinstance(result, dict))
        assert("specs" in result)
        assert(all(isinstance(x, TaskSpec) for x in result['specs']))
        assert(all(x.extra['aKey'] in ["first", "second", "third"] for x in result['specs']))
        assert(len(result['specs']) == 3)

    def test_expander_with_dict_injection(self, spec, state):
        state.update(dict(_task_name=TaskName.build("agroup::basic"),
                          inject={"replace": ["aKey"], "copy":{"other":"blah"}},
                          base="base::task"))

        state['from']          = ["first", "second", "third"]
        jqa    = JobExpandAction()
        result = jqa(spec, state)
        assert(isinstance(result, dict))
        assert("specs" in result)
        assert(all(isinstance(x, TaskSpec) for x in result['specs']))
        assert(all(x.extra['aKey'] in ["first", "second", "third"] for x in result['specs']))
        assert(all('other' in x.extra for x in result['specs']))
        assert(len(result['specs']) == 3)


class TestJobMatcher:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": TaskName.build("agroup::basic")}

    def test_sanity(self):
        pass

class TestJobGenerate:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": TaskName.build("agroup::basic")}

    def test_sanity(self):
        pass
