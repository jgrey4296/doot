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
from doot._structs.task_spec import TaskSpec
from doot.task import DootTask

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
        match InjectSpec.build({"from_spec":["a"]}):
            case InjectSpec():
                assert(True)
            case x:
                assert(False), x

@pytest.mark.xfail
class TestInjectSpecConstraintChecking:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

class TestInjectionApplication:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_basic(self):
        match InjectSpec.build({"from_spec":["blah"]}):
            case InjectSpec():
                assert(True)
            case x:
                 assert(False), x

    def test_apply_from_spec(self):
        injection = InjectSpec.build({"from_spec":["blah"]})
        parent    = TaskSpec.build({"name": "simple::parent", "blah": "bloo"})
        match injection.apply_from_spec(parent):
            case {"blah":"bloo"}:
                assert(True)
            case x:
                 assert(False), x

    def test_apply_from_spec_only(self):
        injection = InjectSpec.build({"from_spec":["blah"], "from_state":["aweg"]})
        parent    = TaskSpec.build({"name": "simple::parent", "blah": "bloo", "aweg": "other"})
        match injection.apply_from_spec(parent):
            case {"aweg": "other"}:
                assert(False)
            case {"blah":"bloo"}:
                assert(True)
            case x:
                 assert(False), x

    def test_apply_from_state(self):
        injection   = InjectSpec.build({"from_spec":["blah"], "from_state":["aweg"]})
        parent_spec = TaskSpec.build({"name": "simple::parent", "blah": "bloo", "aweg": "other"})
        parent_task = DootTask(parent_spec)
        parent_task.state['aweg'] = "task_state"
        match injection.apply_from_state(parent_task):
            case {"aweg": "other"}:
                assert(False)
            case {"aweg": "task_state"}:
                assert(True)
            case x:
                assert(False), x
