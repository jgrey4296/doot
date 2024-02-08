#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import warnings

import pytest

##-- end imports

import random
import doot
import doot.errors
from doot.structs import DootTaskSpec, DootCodeReference
from doot._abstract import TaskBase_i

logging = logmod.root

##-- pytest reminder
# caplog
# mocker.patch | patch.object | patch.multiple | patch.dict | stopall | stop | spy | stub
# pytest.mark.filterwarnings
# pytest.parameterize
# pytest.skip | skipif | xfail
# with pytest.deprecated_call
# with pytest.raises
# with pytest.warns(warntype)

##-- end pytest reminder

matcher_ref        = DootCodeReference.from_str("doot.task.base_job:DootJob").add_mixins("doot.mixins.job.matcher:PatternMatcherMixin")
MatcherBuilder     = matcher_ref.try_import()

base_exts          = [".bib", ".json", ".txt"]
base_mapping       = {".bib": "bib::simple", ".json": "json::simple", ".txt":"txt::simple"}

class ExampleGenerator():

    def _build_subs(self) -> Generator[DootTaskSpec]:
        exts = self.spec.extra.on_fail(base_exts, list).exts()
        for x in range(0, self.spec.extra.on_fail(5, int).subnum()):
            pretend_path = pl.Path("pretend").with_suffix(random.choice(exts))
            yield DootTaskSpec.from_dict({"name": f"subtask_{x}", "fpath": pretend_path})

class SimpleMatcher(MatcherBuilder, ExampleGenerator):
    pass


class TestMatcher:

    @pytest.mark.parametrize("count", [1, 5, 10, 4, 11])
    def test_initial(self, count):
        obj = SimpleMatcher(DootTaskSpec.from_dict({"name":"test::basic", "subnum":count, "match_map":base_mapping, "match_fn":"ext"}))
        assert(isinstance(obj, TaskBase_i))
        subs = list(obj._build_subs())
        assert(len(subs) == count)

    @pytest.mark.parametrize("count", [1, 5, 10, 4, 11])
    def test_mapping(self, count):
        obj = SimpleMatcher(DootTaskSpec.from_dict({"name":"test::basic", "subnum":count, "match_map":base_mapping, "match_fn":"ext"}))
        assert(isinstance(obj, TaskBase_i))
        tasks = list(obj._build_subs())
        for task in tasks:
            match task.extra.fpath.suffix:
                case ".bib":
                    assert(task.ctor == "bib::simple")
                case ".json":
                    assert(task.ctor == "json::simple")
                case ".txt":
                    assert(task.ctor == "txt::simple")

    @pytest.mark.parametrize("count", [1, 5, 10, 4, 11])
    def test_mapping_failure(self, count):
        mapping = {".not": "blah::bloo"}
        obj = SimpleMatcher(DootTaskSpec.from_dict(
            {"name":"test::basic",
             "subnum":count,
             "match_map":mapping,
             "match_fn":"ext"}
                            ))
        assert(isinstance(obj, TaskBase_i))
        with pytest.raises(doot.errors.DootTaskError):
            list(obj._build_subs())
