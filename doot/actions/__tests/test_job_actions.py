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

import doot
doot._test_setup()
import doot.errors
from doot.structs import DootKey, DootTaskSpec, DootActionSpec, DootTaskName
import doot.actions.job_actions as JA

printer = logmod.getLogger("doot._printer")
logging = logmod.root

class TestJobActions:

    @pytest.fixture(scope="function")
    def spec(self):
        return DootActionSpec.build({"do": "action", "args":["test::simple", "test::other"], "update_":"specs"})

    @pytest.fixture(scope="function")
    def state(self):
        return {"_task_name": DootTaskName.build("basic")}

    @pytest.fixture(scope="function")
    def cleanup(self):
        pass

    def test_initial(self, spec, state):
        jqa    = JA.JobQueueAction()
        result = jqa(spec, state)
        assert(isinstance(result, list))

    def test_basic(self, spec, state):
        jqa    = JA.JobQueueAction()
        result = jqa(spec, state)
        assert(isinstance(result, list))
        assert(len(result) == 2)
        assert(all(isinstance(x, DootTaskSpec) for x in result))

    def test_basic_expander(self, spec, state):
        state.update(dict(_task_name=DootTaskName.build("basic"),
                          inject={"replace":["aKey"]},
                          base="base::task"))

        state['from'] = ["first", "second", "third"]
        jqa    = JA.JobExpandAction()
        result = jqa(spec, state)
        assert(isinstance(result, dict))
        assert("specs" in result)
        assert(all(isinstance(x, DootTaskSpec) for x in result['specs']))
        assert(all(x.extra['aKey'] in ["first", "second", "third"] for x in result['specs']))
        assert(len(result['specs']) == 3)

    def test_expander_with_dict_injection(self, spec, state):
        state.update(dict(_task_name=DootTaskName.build("basic"),
                          inject={"replace": ["aKey"], "copy":{"other":"blah"}},
                          base="base::task"))

        state['from']          = ["first", "second", "third"]
        jqa    = JA.JobExpandAction()
        result = jqa(spec, state)
        assert(isinstance(result, dict))
        assert("specs" in result)
        assert(all(isinstance(x, DootTaskSpec) for x in result['specs']))
        assert(all(x.extra['aKey'] in ["first", "second", "third"] for x in result['specs']))
        assert(all('other' in x.extra for x in result['specs']))
        assert(len(result['specs']) == 3)


class TestJobWalker:
    @pytest.mark.skip
    def test_walker(self, spec, state):
        pass


class TestJobLimiter:
    @pytest.mark.skip
    def test_limiter(self, spec, state):
        pass
