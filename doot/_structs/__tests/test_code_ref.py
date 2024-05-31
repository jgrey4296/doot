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

import tomlguard
import doot
doot._test_setup()

from doot._structs.code_ref import CodeReference
from doot.task.base_task import DootTask

class TestCodeReference:

    def test_basic(self):
        ref = CodeReference.build("doot.task.base_task:DootTask")
        assert(isinstance(ref, CodeReference))


    def test_head(self):
        ref = CodeReference.build("doot.task.base_task:DootTask")
        assert(ref.head == ["doot", "task", "base_task"])


    def test_tail(self):
        ref = CodeReference.build("doot.task.base_task:DootTask")
        assert(ref.tail == ["DootTask"])


    def test_import(self):
        ref = CodeReference.build("doot.task.base_task:DootTask")
        imported = ref.try_import()
        assert(isinstance(imported, type))
        assert(imported == DootTask)

    def test_import_module_fail(self):
        ref = CodeReference.build("doot.taskSSSSS.base_task:DootTask")
        with pytest.raises(ImportError):
            imported = ref.try_import()

    def test_import_class_fail(self):
        ref = CodeReference.build("doot.task.base_task:DootTaskSSSSSS")
        with pytest.raises(ImportError):
            imported = ref.try_import()

    @pytest.mark.skip(reason="mixins obsolete")
    def test_add_mixin(self):
        ref = CodeReference.build("doot.task.base_task:DootTask")
        assert(not bool(ref._mixins))
        ref_plus = ref.add_mixins("doot.mixins.job.terse:TerseBuilder_M")
        assert(ref is not ref_plus)
        assert(not bool(ref._mixins))
        assert(bool(ref_plus._mixins))

    @pytest.mark.skip(reason="mixins obsolete")
    def test_build_mixin(self):
        ref      = CodeReference.build("doot.task.base_task:DootTask")
        ref_plus = ref.add_mixins("doot.mixins.job.terse:TerseBuilder_M")
        result   = ref_plus.try_import()
        assert(result != DootTask)
        assert(DootTask in result.mro())
