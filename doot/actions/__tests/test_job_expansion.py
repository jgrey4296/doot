#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import warnings
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest

# ##-- end 3rd party imports

logging = logmod.root

# ##-- 1st party imports
import doot

# ##-- end 1st party imports

doot._test_setup()
# ##-- 1st party imports
import doot.errors
from doot.actions.job_expansion import JobExpandAction, JobMatchAction
from doot.structs import ActionSpec, DKey, TaskName, TaskSpec

# ##-- end 1st party imports


class TestJobExpansion:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "job.expand", "args":[], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": TaskName("agroup::basic")}

    def test_sanity(self, spec, state):
        obj = JobExpandAction()
        assert(isinstance(obj, JobExpandAction))

    def test_empty_expansion(self, spec, state):
        obj = JobExpandAction()
        result = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(len(result['specs']) == 0)

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
        state['inject'] = {"insert": ['target']}
        obj = JobExpandAction()
        result = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(len(result['specs']) == 3)
        for spec, expect in zip(result['specs'], args):
            assert(spec.target == expect)

    def test_action_template(self, spec, state):
        state['template'] = "test::task"
        state['from']     = [1]
        obj               = JobExpandAction()
        result            = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(result['specs'][0].sources == ["test::task"])
        assert(len(result['specs'][0].actions) == 0)

    def test_taskname_template(self, spec, state):
        state['template'] = [{"do":"basic"}, {"do":"basic"}, {"do":"basic"}]
        state['from'] = [1]
        obj = JobExpandAction()
        result = obj(spec, state)
        assert(isinstance(result, dict))
        assert(isinstance(result[spec.kwargs['update_']], list))
        assert(len(result['specs'][0].actions) == 3)


    def test_basic_expander(self, spec, state):
        state.update(dict(_task_name=TaskName("agroup::basic"),
                          inject={"insert":["aKey"]},
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
        state.update(dict(_task_name=TaskName("agroup::basic"),
                          inject={"insert": ["aKey"], "delay":{"other":"blah"}},
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
        return {"_task_name": TaskName("agroup::basic")}

    def test_sanity(self):
        pass

class TestJobGenerate:

    @pytest.fixture(scope="function")
    def spec(self):
        return ActionSpec.build({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": TaskName("agroup::basic")}

    def test_sanity(self):
        pass
