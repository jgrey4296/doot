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
import doot
doot._test_setup()
from doot.structs import DootKey
from doot.utils.testing_fixtures import wrap_locs
from doot.utils import action_decorators as decs
from doot.utils.decorators import DecorationUtils as DU

logging = logmod.root

DD = decs.DootDecorator

class TestDecorators:

    @pytest.fixture(scope="function")
    def setup(self):
        pass

    @pytest.fixture(scope="function")
    def cleanup(self):
        pass

    def test_initial(self):
        """ check a simple annotation and wrap """

        @decs.DryRunSwitch()
        def simple(spec:dict, state:dict) -> str:
            return "blah"

        assert(DU.has_annotations(simple, doot.constants.decorations.RUN_DRY_SWITCH))
        assert(simple({}, {}) == "blah")

    def test_override_dry_run(self):
        """ check the wrapper works """

        @decs.DryRunSwitch(override=True)
        def simple(spec:dict, state:dict) -> str:
            return "blah"

        assert(DU.has_annotations(simple, doot.constants.decorations.RUN_DRY_SWITCH))
        assert(simple({}, {}) is None)

    def test_wrap_method(self):

        @decs.DryRunSwitch()
        class SimpleClass:

            def __call__(self, spec, state):
                return "blah"

        # class is annotated
        assert(DU.has_annotations(SimpleClass, doot.constants.decorations.RUN_DRY_SWITCH))
        # Instance is annotated
        assert(DU.has_annotations(SimpleClass(), doot.constants.decorations.RUN_DRY_SWITCH))
        assert(SimpleClass()({}, {}) == "blah")

    def test_wrap_method_override_dry(self):

        @decs.DryRunSwitch(override=True)
        class SimpleClass:

            def __call__(self, spec, state):
                return "blah"

        # class is annotated
        assert(DU.has_annotations(SimpleClass, doot.constants.decorations.RUN_DRY_SWITCH))
        # Instance is annotated
        assert(DU.has_annotations(SimpleClass(), doot.constants.decorations.RUN_DRY_SWITCH))
        assert(SimpleClass()({}, {}) is None)

    def test_annotate_fn(self):

        @decs.RunsDry()
        def simple(spec:dict, state:dict) -> str:
            return "blah"

        assert(DU.has_annotations(simple, doot.constants.decorations.RUN_DRY))

    def test_annotate_method(self):

        @decs.RunsDry()
        class SimpleClass:

            def __call__(self, spec:dict, state:dict) -> str:
                return "blah"

        assert(DU.has_annotations(SimpleClass, doot.constants.decorations.RUN_DRY))
        assert(DU.has_annotations(SimpleClass(), doot.constants.decorations.RUN_DRY))

    def test_annotation_survives_subclassing(self):

        @decs.RunsDry()
        class SimpleSuper:
            pass

        class SimpleChild(SimpleSuper):
            pass

        assert(DU.has_annotations(SimpleSuper,   decs.RUN_DRY))
        assert(DU.has_annotations(SimpleSuper(), decs.RUN_DRY))
        assert(DU.has_annotations(SimpleChild,   decs.RUN_DRY))
        assert(DU.has_annotations(SimpleChild(), decs.RUN_DRY))


    def test_key_decoration_survives_annotation(self):

        @decs.RunsDry()
        @DootKey.dec.expands("blah")
        def simple(spec, state, blah):
            return blah

        assert(DU.has_annotations(simple,   decs.RUN_DRY))
        assert(simple(None, {"blah":"bloo"}) == "bloo")


    def test_wrapper_survives_key_decoration(self):

        @decs.DryRunSwitch(override=True)
        @DootKey.dec.expands("blah")
        def simple(spec:dict, state:dict, blah:str) -> str:
            """ a simple test func """
            return blah

        assert(DU.has_annotations(simple,   decs.RUN_DRY_SWITCH))
        assert(simple(None, {"blah": "bloo"}) is None)


    def test_wrapper_survives_method_key_decoration(self):

        @decs.DryRunSwitch(override=True)
        class SimpleAction:

            @DootKey.dec.expands("blah")
            def __call__(self, spec:dict, state:dict, blah:str) -> str:
                """ a simple test func """
                return blah

        assert(DU.has_annotations(SimpleAction,   decs.RUN_DRY_SWITCH))
        assert(SimpleAction()({}, {"blah": "bloo"}) is None)


    def test_setting_dryswitch_on_method(self):

        class SimpleAction:

            @decs.DryRunSwitch(override=True)
            @DootKey.dec.expands("blah")
            def __call__(self, spec:dict, state:dict, blah:str) -> str:
                """ a simple test func """
                return blah

        assert(DU.has_annotations(SimpleAction.__call__,   decs.RUN_DRY_SWITCH))
        assert(SimpleAction()({}, {"blah": "bloo"}) is None)

    def test_wrapping_overriden_by_subclassing(self):

        @decs.DryRunSwitch(override=True)
        class SimpleSuper:

            def __call__(self, spec, state):
                return "blah"

        class SimpleChild(SimpleSuper):

            def __call__(self, spec, state):
                return "blah"

        assert(SimpleSuper()({}, {}) is None)
        assert(SimpleChild()({}, {}) == "blah")

    def test_gens_tasks(self):

        @decs.GeneratesTasks()
        def simple(spec, state):
            return []

        assert(DU.has_annotations(simple, decs.GEN_TASKS))
        assert(isinstance(simple({},{}), list))


    def test_gens_tasks_raises_error(self):

        @decs.GeneratesTasks()
        def simple(spec, state):
            return "blah"

        assert(DU.has_annotations(simple, decs.GEN_TASKS))
        with pytest.raises(doot.errors.DootActionError):
            simple({},{})


    def test_io_writer_check(self, wrap_locs):
        doot.locs.update({"blah" : dict(loc="blah", protected=True) })

        @decs.IOWriter()
        @DootKey.dec.paths("to")
        def simple(spec, state, to):
            return "blah"

        assert(DU.has_annotations(simple, decs.IO_ACT))
        with pytest.raises(doot.errors.DootTaskError):
            simple(None, {"to": "{blah}"})


    def test_io_writer_pas(self, wrap_locs):
        doot.locs.update({"blah" : dict(loc="blah", protected=False) })

        @decs.IOWriter()
        @DootKey.dec.paths("to")
        def simple(spec, state, to):
            "a simple docstring "
            return "blah"

        assert(DU.has_annotations(simple, decs.IO_ACT))
        assert(simple(None, {"to": "{blah}"}) == "blah")
