#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN201, ARG001, ANN001, ARG002, ANN202

# Imports:
# Imports
from __future__ import annotations

# ##-- stdlib imports
import logging as logmod
import pathlib as pl
import warnings
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
from jgdv.structs.dkey import DKey

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._structs.inject_spec import InjectSpec


# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
import typing
from typing import Generic, cast, assert_type, assert_never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload
# from dataclasses import InitVar, dataclass, field
# from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError

if typing.TYPE_CHECKING:
   from jgdv import Maybe
   from typing import Final
   from typing import ClassVar, Any, LiteralString
   from typing import Never, Self, Literal
   from typing import TypeGuard
   from collections.abc import Iterable, Iterator, Callable, Generator
   from collections.abc import Sequence, Mapping, MutableMapping, Hashable

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:

# Body:

class TestInjectSpec:

    @pytest.fixture(scope="function")
    def setup(self):
        pass

    @pytest.fixture(scope="function")
    def cleanup(self):
        pass

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        match InjectSpec():
            case InjectSpec():
                assert(True)
            case x:
                assert(False), x

    def test_build_none(self):
        match InjectSpec.build({}):
            case None:
                assert(True)
            case x:
                assert(False), x

    def test_build_something(self):
        match InjectSpec.build({"now":["a"]}):
            case InjectSpec():
                assert(True)
            case x:
                assert(False), x

    def test_as_dict(self):
        match InjectSpec.build({"now":["a"]}).as_dict():
            case dict():
                assert(True)
            case x:
                assert(False), x

    def test_expansion_now_list(self):
        source = {"a": "blah"}
        match InjectSpec.build({"now":["a"]}, sources=[source]).as_dict():
            case {"a":"blah"}:
                assert(True)
            case x:
                assert(False), x


    def test_expansion_now_dict(self):
        source = {"a": "blah", "b":"aweg"}
        match InjectSpec.build({"now":{"a": "{b}"}}, sources=[source]).as_dict():
            case {"a":"aweg"}:
                assert(True)
            case x:
                assert(False), x

    def test_expansion_now_repeated_list(self):
        source = {"a": "{blah}", "blah": "bloo"}
        match InjectSpec.build({"now":["a"]}, sources=[source]).as_dict():
            case {"a":"bloo"}:
                assert(True)
            case x:
                assert(False), x

    def test_expansion_delay_list(self):
        source = {"a": "{blah}", "blah": "bloo"}
        match InjectSpec.build({"delay":["a"]}, sources=[source]).as_dict():
            case {"a": DKey() as x} if x == "blah":
                assert(True)
            case x:
                assert(False), x


    def test_expansion_delay_dict(self):
        source = {"a": "{blah}", "blah": "bloo", "b": "{aweg}", "aweg": "qqqq"}
        match InjectSpec.build({"delay":{"a": "{b}"}}, sources=[source]).as_dict():
            case {"a": DKey() as x} if x == "aweg":
                assert(True)
            case x:
                assert(False), x


    def test_insert(self):
        source = {"a": "{blah}", "blah": "bloo"}
        match InjectSpec.build({"insert":["a"]}, sources=[source], insertion="aweg").as_dict():
            case {"a": str() as x} if x == "aweg":
                assert(True)
            case x:
                assert(False), x


    def test_insert_dict(self):
        source = {"a": "{blah}", "blah": "bloo"}
        match InjectSpec.build({"insert":{"a": "a", "b": "blah"}}, sources=[source], insertion="aweg").as_dict():
            case {"a":"a", "b": "blah"}:
                assert(True)
            case x:
                assert(False), x


    def test_suffix(self):
        source = {"a": "{blah}", "blah": "bloo"}
        match InjectSpec.build({"suffix":"blah"}).as_dict():
            case {"_add_suffix":"blah"}:
                assert(True)
            case x:
                assert(False), x


    def test_constraints_pass(self):
        """ injection ⊂ constraints """
        constraint = {"a": 1, "b": 2}
        source = {"a": "{blah}", "blah": "bloo"}
        match InjectSpec.build({"now" : ["a"]}).as_dict(constraint=constraint):
            case dict():
                assert(True)
            case x:
                assert(False), x


    def test_constraints_fail(self):
        """ 'a' is injected unexpectedly
        injection ⊄ injection
        """
        constraint = {"b": 2}
        source = {"a": "{blah}", "blah": "bloo"}
        with pytest.raises(doot.errors.StateError):
            InjectSpec.build({"now" : ["a"]}).as_dict(constraint=constraint)


    def test_constraints_required(self):
        """ 'a' is expected and missing from constraint defaults """
        constraint = {"b": 2, 'must_inject': ["a"]}
        source     = {"a": "{blah}", "blah": "bloo"}
        match InjectSpec.build({"now" : ["a"]}).as_dict(constraint=constraint):
            case dict():
                assert(True)
            case x:
                assert(False), x


    def test_constraints_required_fail(self):
        """ 'a' is expected and missing from constraint defaults """
        constraint = {"b": 2, 'must_inject': ["a"]}
        source     = {"a": "{blah}", "b": "bloo"}
        with pytest.raises(doot.errors.StateError):
            InjectSpec.build({"now" : ["blah"]}).as_dict(constraint=constraint)
