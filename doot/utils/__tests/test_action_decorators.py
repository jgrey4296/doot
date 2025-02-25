#!/usr/bin/env python3
"""

"""
# ruff: noqa: ANN201 ARG001 ANN001 ARG002 ANN202 C408
# Imports
from __future__ import annotations

import logging as logmod
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
import warnings

import pytest
import doot
from doot.structs import DKey, DKeyed
from doot.utils.testing_fixtures import wrap_locs
from doot.utils import action_decorators as decs

logging = logmod.root

class TestDryRunSwitch:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_initial(self):
        """ check a simple annotation and wrap """

        @decs.DryRunSwitch()
        def simple(spec:dict, state:dict) -> str:
            return "blah"

        dec = decs.DryRunSwitch()
        assert(dec.is_marked(simple))
        assert(simple({}, {}) == "blah")

    def test_override_dry_run(self):
        """ check the wrapper works """
        dec = decs.DryRunSwitch(override=True)

        @dec
        def simple(spec:dict, state:dict) -> str:
            return "blah"

        assert(dec.is_marked(simple))
        assert(simple({}, {}) is None)

    def test_wrap_class(self):

        @decs.DryRunSwitch()
        class SimpleClass:

            def __call__(self, spec, state):
                return "blah"

        dec = decs.DryRunSwitch()
        # class is annotated
        assert(dec.is_marked(SimpleClass))
        # Instance is annotated
        assert(SimpleClass()({}, {}) == "blah")

    def test_wrap_class_override_dry(self):

        @decs.DryRunSwitch(override=True)
        class SimpleClass:

            def __call__(self, spec, state):
                return "blah"

        dec = decs.DryRunSwitch()
        # class is annotated
        assert(dec.is_marked(SimpleClass))
        # Instance is annotated
        inst = SimpleClass()
        assert(inst({}, {}) is None)

    def test_wrapper_survives_key_decoration(self):

        @decs.DryRunSwitch(override=True)
        @DKeyed.expands("blah")
        def simple(spec:dict, state:dict, blah:str) -> str:
            """ a simple test func """
            return blah

        dec = decs.DryRunSwitch()
        assert(dec.is_marked(simple))
        assert(simple(None, {"blah": "bloo"}) is None)

    def test_wrapper_survives_method_key_decoration(self):

        @decs.DryRunSwitch(override=True)
        class SimpleAction:

            @DKeyed.expands("blah")
            def __call__(self, spec:dict, state:dict, blah:str) -> str:
                """ a simple test func """
                return blah

        assert(decs.DryRunSwitch().is_marked(SimpleAction))
        assert(SimpleAction()({}, {"blah": "bloo"}) is None)

    def test_setting_dryswitch_on_method(self):

        @decs.DryRunSwitch(override=True)
        class SimpleAction:

            @DKeyed.expands("blah")
            def __call__(self, spec:dict, state:dict, blah:str) -> str:
                """ a simple test func """
                return blah

        assert(decs.DryRunSwitch().is_marked(SimpleAction))
        assert(SimpleAction()({}, {"blah": "bloo"}) is None)

    def test_wrapping_overriden_by_subclassing(self):

        @decs.DryRunSwitch(override=True)
        class SimpleSuper:

            def __call__(self, spec, state):
                return "blah"

        class SimpleChild(SimpleSuper):

            def __call__(self, spec, state):
                return "blah"

        assert(decs.DryRunSwitch().is_marked(SimpleSuper))
        assert(not decs.DryRunSwitch().is_marked(SimpleChild))
        assert(SimpleSuper()({}, {}) is None)
        assert(SimpleChild()({}, {}) == "blah")

class TestGenerateTasksDec:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_gens_tasks(self):

        @decs.GeneratesTasks()
        def simple(spec, state):
            return []

        assert(decs.GeneratesTasks().is_marked(simple))
        assert(isinstance(simple({},{}), list))

    def test_gens_tasks_raises_error(self):

        @decs.GeneratesTasks()
        def simple(spec, state):
            return "blah"

        assert(decs.GeneratesTasks().is_marked(simple))
        with pytest.raises(doot.errors.ActionCallError):
            simple({},{})


@pytest.mark.xfail
class TestIOWriterMark:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_io_writer_check(self, wrap_locs):
        """ check IOWriter guards locations """
        doot.locs.update({"blah" : dict(loc="blah", protected=True) })

        @decs.IOWriter()
        @DKeyed.paths("to")
        def simple(spec, state, to):
            return "blah"

        assert(decs.IOWriter().is_marked(simple))
        # assert(DU.has_annotations(simple, decs.IO_ACT))
        with pytest.raises(doot.errors.TaskError):
            simple(None, {"to": "{blah}"})

    def test_io_writer_pass(self, wrap_locs):
        doot.locs.update({"blah" : dict(path="blah", protected=False) })

        @decs.IOWriter()
        @DKeyed.paths("to")
        def simple(spec, state, to):
            "a simple docstring "
            return "blah"

        # assert(DU.has_annotations(simple, decs.IO_ACT))
        assert(simple(None, {"to": "{blah}"}) == "blah")
