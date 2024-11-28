#!/usr/bin/env python2
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
from jgdv.decorators.util import DecorationUtils as DU
import doot
doot._test_setup()
from doot.structs import DKey, DKeyed
from doot.utils.testing_fixtures import wrap_locs
from doot.utils import action_decorators as decs

logging = logmod.root


class TestDecorators:

    def test_initial(self):
        """ check a simple annotation and wrap """

        @decs.DryRunSwitch()
        def simple(spec:dict, state:dict) -> str:
            return "blah"

        dec = decs.DryRunSwitch()
        assert(dec._is_marked(simple))
        assert(simple({}, {}) == "blah")

    def test_override_dry_run(self):
        """ check the wrapper works """
        dec = decs.DryRunSwitch(override=True)

        @dec
        def simple(spec:dict, state:dict) -> str:
            return "blah"

        assert(dec._is_marked(simple))
        assert(simple({}, {}) is None)

    def test_wrap_method(self):

        class SimpleClass:

            @decs.DryRunSwitch()
            def __call__(self, spec, state):
                return "blah"

        dec = decs.DryRunSwitch()
        # class is annotated
        assert(dec._is_marked(SimpleClass))
        # Instance is annotated
        assert(SimpleClass()({}, {}) == "blah")

    def test_wrap_method_override_dry(self):

        class SimpleClass:

            @decs.DryRunSwitch(override=True)
            def __call__(self, spec, state):
                return "blah"

        dec = decs.DryRunSwitch()
        # class is annotated
        assert(dec._is_marked(SimpleClass))
        # Instance is annotated
        assert(SimpleClass()({}, {}) is None)

    def test_annotate_fn(self):

        @decs.RunsDry()
        def simple(spec:dict, state:dict) -> str:
            return "blah"

        assert(decs.RunsDry()._is_marked(simple))

    def test_annotate_method(self):

        class SimpleClass:

            @decs.RunsDry()
            def __call__(self, spec:dict, state:dict) -> str:
                return "blah"

        assert(decs.RunsDry()._is_marked(SimpleClass))

    def test_annotation_survives_subclassing(self):

        class SimpleSuper:

            @decs.RunsDry()
            def __call__():
                pass

        class SimpleChild(SimpleSuper):
            pass

        assert(decs.RunsDry()._is_marked(SimpleSuper))
        assert(decs.RunsDry()._is_marked(SimpleChild))


    @pytest.mark.xfail
    def test_key_decoration_survives_annotation(self):

        @decs.RunsDry()
        @DKeyed.formats("blah")
        def simple(spec, state, blah):
            return blah

        assert(decs.RunsDry()._is_marked(simple))
        assert(simple(None, {"blah":"bloo"}) == "bloo")


    def test_wrapper_survives_key_decoration(self):

        @decs.DryRunSwitch(override=True)
        @DKeyed.expands("blah")
        def simple(spec:dict, state:dict, blah:str) -> str:
            """ a simple test func """
            return blah

        dec = decs.DryRunSwitch()
        assert(dec._is_marked(simple))
        assert(simple(None, {"blah": "bloo"}) is None)


    def test_wrapper_survives_method_key_decoration(self):

        class SimpleAction:

            @decs.DryRunSwitch(override=True)
            @DKeyed.expands("blah")
            def __call__(self, spec:dict, state:dict, blah:str) -> str:
                """ a simple test func """
                return blah

        assert(decs.DryRunSwitch()._is_marked(SimpleAction))
        assert(SimpleAction()({}, {"blah": "bloo"}) is None)


    def test_setting_dryswitch_on_method(self):

        class SimpleAction:

            @decs.DryRunSwitch(override=True)
            @DKeyed.expands("blah")
            def __call__(self, spec:dict, state:dict, blah:str) -> str:
                """ a simple test func """
                return blah

        assert(decs.DryRunSwitch()._is_marked(SimpleAction.__call__))
        assert(decs.DryRunSwitch()._is_marked(SimpleAction))
        assert(SimpleAction()({}, {"blah": "bloo"}) is None)

    def test_wrapping_overriden_by_subclassing(self):

        class SimpleSuper:

            @decs.DryRunSwitch(override=True)
            def __call__(self, spec, state):
                return "blah"

        class SimpleChild(SimpleSuper):

            def __call__(self, spec, state):
                return "blah"

        assert(decs.DryRunSwitch()._is_marked(SimpleSuper))
        assert(not decs.DryRunSwitch()._is_marked(SimpleChild))
        assert(SimpleSuper()({}, {}) is None)
        assert(SimpleChild()({}, {}) == "blah")

    def test_gens_tasks(self):

        @decs.GeneratesTasks()
        def simple(spec, state):
            return []

        assert(decs.GeneratesTasks()._is_marked(simple))
        assert(isinstance(simple({},{}), list))


    def test_gens_tasks_raises_error(self):

        @decs.GeneratesTasks()
        def simple(spec, state):
            return "blah"

        assert(decs.GeneratesTasks()._is_marked(simple))
        with pytest.raises(doot.errors.DootActionError):
            simple({},{})


    @pytest.mark.xfail
    def test_io_writer_check(self, wrap_locs):
        """ check IOWriter guards locations """
        doot.locs.update({"blah" : dict(loc="blah", protected=True) })

        @decs.IOWriter()
        @DKeyed.paths("to")
        def simple(spec, state, to):
            return "blah"

        assert(decs.IOWriter()._is_marked(simple))
        assert(DU.has_annotations(simple, decs.IO_ACT))
        with pytest.raises(doot.errors.DootTaskError):
            simple(None, {"to": "{blah}"})



    @pytest.mark.xfail
    def test_io_writer_pass(self, wrap_locs):
        doot.locs.update({"blah" : dict(path="blah", protected=False) })

        @decs.IOWriter()
        @DKeyed.paths("to")
        def simple(spec, state, to):
            "a simple docstring "
            return "blah"

        assert(DU.has_annotations(simple, decs.IO_ACT))
        assert(simple(None, {"to": "{blah}"}) == "blah")
