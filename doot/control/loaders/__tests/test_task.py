#!/usr/bin/env python3
"""

"""
# ruff: noqa: ERA001, ANN202, ANN001, PLR2004, ARG002
#
##-- imports
from __future__ import annotations

import logging as logmod
import unittest
import warnings
import pathlib as pl
from typing import (Any, Callable, ClassVar, Generic, Iterable, Iterator,
                    Mapping, Match, MutableMapping, Sequence, Tuple, TypeAlias,
                    TypeVar, cast)
##-- end imports

import pytest
import importlib.metadata
import doot
from jgdv.structs.chainguard import ChainGuard
from doot.workflow._interface import TaskMeta_e

from doot.workflow import TaskSpec
from doot.util.mock_gen import mock_entry_point, mock_task_ctor

from doot.control.loaders import task
logging          = logmod.root

job_ctor_str     = "doot.workflow:DootJob"
task_ctor_str    = "doot.workflow:DootTask"
bad_ctor_str     = "doot.workflow:DoesntExistJob"
bad_mod_str      = "doot.workflow.bad:DootJob"
bad_alias_str    = "doesntexist"
bad_two_part_str = "doot:bad"
basic_alias_str  = "basic"
##--|
class TestTaskLoader:

    def test_initial(self):
        basic = task.TaskLoader()
        assert(basic is not None)

    def test_basic__internal_load(self):
        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : job_ctor_str})
        basic = task.TaskLoader()
        basic.setup({})
        result = basic._get_raw_specs_from_data(ChainGuard(specs).tasks, "test_file")

        assert(isinstance(result, list))
        assert(len(result) == 1)
        assert(result[0]['name'] == "test")

    def test_basic_load(self, mocker):
        specs = {"tasks": {"basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "ctor" : job_ctor_str})
        basic = task.TaskLoader()
        mocker.patch.object(basic, "_load_specs_from_path")
        basic.setup({}, specs)
        result = basic.load()

        assert(isinstance(result, ChainGuard))
        assert(len(result) == 1)
        assert("basic::test" in result)
        assert(isinstance(result['basic::test'], TaskSpec))

    def test_multi_load(self, mocker):
        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "ctor" : job_ctor_str})
        specs['tasks']['basic'].append({"name"  : "other", "ctor": job_ctor_str})
        basic = task.TaskLoader()
        mocker.patch.object(basic, "_load_specs_from_path")
        basic.setup({}, specs)
        result = basic.load()

        assert(isinstance(result, ChainGuard))
        assert(len(result) == 2)
        assert("basic::test" in result)
        assert("basic::other" in result)

    def test_name_error_on_overload(self, mocker, caplog):
        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "ctor" : job_ctor_str})
        specs['tasks']['basic'].append({"name"  : "test", "ctor": job_ctor_str})
        basic = task.TaskLoader()
        basic.exit_on_load_failures = True
        mocker.patch.object(basic, "_load_specs_from_path")
        basic.setup({}, specs)
        assert(not bool(basic.tasks))
        task.allow_overloads = False
        with pytest.raises(doot.errors.StructLoadError):
            basic.load()

    def test_cmd_name_conflict_doesnt_error(self, mocker):
        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "ctor" : job_ctor_str})
        basic = task.TaskLoader()
        mocker.patch.object(basic, "_load_specs_from_path")
        basic.setup({}, specs)
        basic.cmd_names = {"test"}

        assert(not bool(basic.tasks))
        assert(not bool(basic.failures))
        result = basic.load()
        assert(bool(result))

    def test_bad_task_class(self, mocker):
        specs = {"tasks": { "basic": []}}
        specs['tasks']['basic'].append({"name"  : "test", "ctor" : bad_ctor_str})

        basic = task.TaskLoader()
        mocker.patch.object(basic, "_load_specs_from_path")
        basic.setup({}, specs)

        result = basic.load()
        assert(TaskMeta_e.DISABLED in  result["basic::test"].meta)

    def test_bad_task_module(self, mocker):
        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "ctor" : bad_mod_str})
        basic = task.TaskLoader()
        mocker.patch.object(basic, "_load_specs_from_path")
        basic.setup({}, specs)

        result = basic.load()
        assert(TaskMeta_e.DISABLED in  result["basic::test"].meta)

    def test_bad_spec(self, mocker):
        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "ctor": bad_alias_str})
        basic = task.TaskLoader()
        basic.exit_on_load_failures = True
        mocker.patch.object(basic, "_load_specs_from_path")
        basic.setup({}, specs)

        with pytest.raises(doot.errors.StructLoadError):
            result = basic.load()

    def test_task_type_empty(self, mocker):
        specs = {"tasks": {"basic": []}}
        specs['tasks']['basic'].append({"name": "simple"})

        mock_ctor                   = mock_task_ctor()
        mock_ep                     = mock_entry_point(name="basic", value=mock_ctor)

        plugins                     = ChainGuard({"task": [mock_ep]})
        basic                       = task.TaskLoader()
        mocker.patch.object(basic, "_load_specs_from_path")
        basic.setup(plugins, ChainGuard(specs))

        result    = basic.load()

        assert(len(result) == 1)
        task_spec = result['basic::simple']
        assert(task_spec.ctor is None)


    def test_task_type_specified(self, mocker):
        specs = {"tasks": {"basic": []}}
        specs['tasks']['basic'].append({"name": "simple"})

        mock_ctor                   = mock_task_ctor()
        mock_ep                     = mock_entry_point(name="basic", value=mock_ctor)

        plugins                     = ChainGuard({"task": [mock_ep]})
        basic                       = task.TaskLoader()
        mocker.patch.object(basic, "_load_specs_from_path")
        basic.setup(plugins, ChainGuard(specs))

        result    = basic.load()

        assert(len(result) == 1)
        task_spec = result['basic::simple']
        assert(task_spec.ctor is None)

    def test_task_missing_plugin_results_in_disabled(self, mocker):
        """ a bad ctor alias disables the task """
        mocker.patch("importlib.metadata.EntryPoint")
        specs = {"tasks": {"basic": []}}
        specs['tasks']['basic'].append({"name": "simple", "ctor": bad_two_part_str})

        mock_ep      = importlib.metadata.EntryPoint()
        mock_ep.name = "basic"

        plugins      = ChainGuard({"job": [mock_ep]})
        basic        = task.TaskLoader()
        mocker.patch.object(basic, "_load_specs_from_path")
        basic.setup(plugins, ChainGuard(specs))

        result = basic.load()
        assert(TaskMeta_e.DISABLED in  result["basic::simple"].meta)


    def test_task_bad_type_loaded(self, mocker):
        mocker.patch("importlib.metadata.EntryPoint")
        specs = {"tasks": {"basic": []}}
        specs['tasks']['basic'].append({"name": "simple", "ctor": basic_alias_str})

        mock_ep      = mock_entry_point()

        plugins      = ChainGuard({"job": [mock_ep]})
        basic        = task.TaskLoader()
        basic.exit_on_load_failures = True
        mocker.patch.object(basic, "_load_specs_from_path")
        basic.setup(plugins, ChainGuard(specs))

        with pytest.raises(doot.errors.StructLoadError):
            basic.load()
