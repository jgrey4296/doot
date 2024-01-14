#!/usr/bin/env python3
"""

"""
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
import tomlguard
import doot
from doot.structs import DootTaskSpec
from doot._abstract.task import TaskBase_i
from doot.utils.mock_gen import mock_entry_point, mock_task_ctor

doot.config = tomlguard.TomlGuard({})
from doot.loaders import task_loader
logging = logmod.root

class TestTaskLoader:

    def test_initial(self):
        basic = task_loader.DootTaskLoader()
        assert(basic is not None)

    def test_basic__internal_load(self):
        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_job:DootJob"})
        basic = task_loader.DootTaskLoader()
        basic.setup({})
        result = basic._load_raw_specs(tomlguard.TomlGuard(specs).tasks, "test_file")

        assert(isinstance(result, list))
        assert(len(result) == 1)
        assert(result[0]['name'] == "test")

    def test_basic_load(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_sources")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": {"basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "ctor" : "doot.task.base_job:DootJob"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)
        result = basic.load()

        assert(isinstance(result, tomlguard.TomlGuard))
        assert(len(result) == 1)
        assert("basic::test" in result)
        assert(isinstance(result['basic::test'], DootTaskSpec))

    def test_multi_load(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_sources")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "ctor" : "doot.task.base_job:DootJob"})
        specs['tasks']['basic'].append({"name"  : "other", "ctor": "doot.task.base_job:DootJob"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)
        result = basic.load()

        assert(isinstance(result, tomlguard.TomlGuard))
        assert(len(result) == 2)
        assert("basic::test" in result)
        assert("basic::other" in result)

    def test_name_warn_on_overload(self, mocker, caplog):
        mocker.patch("doot.loaders.task_loader.task_sources")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "ctor" : "doot.task.base_job:DootJob"})
        specs['tasks']['basic'].append({"name"  : "test", "ctor": "doot.task.base_job:DootJob"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)
        task_loader.allow_overloads = False

        basic.load()

        assert("Overloading Task: basic::test : doot.task.base_job:DootJob" in caplog.messages)

    def test_cmd_name_conflict_doesnt_error(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_sources")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "ctor" : "doot.task.base_job:DootJob"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)
        basic.cmd_names = set(["test"])

        result = basic.load()
        assert(bool(result))

    def test_bad_task_class(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_sources")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": { "basic": []}}
        specs['tasks']['basic'].append({"name"  : "test", "ctor" : "doot.task.base_job:DoesntExistJob"})

        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)

        with pytest.raises(doot.errors.DootTaskLoadError):
            basic.load()

    def test_bad_task_module(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_sources")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "ctor" : "doot.task.doesnt_exist_module:DoesntExistJob"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)

        with pytest.raises(doot.errors.DootTaskLoadError):
            basic.load()

    @pytest.mark.xfail
    def test_bad_spec(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_sources")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)

        with pytest.raises(doot.errors.DootTaskLoadError):
            result = basic.load()

    def test_task_type(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_sources")
        mocker.patch("doot._configs_loaded_from")
        specs = {"tasks": {"basic": []}}
        specs['tasks']['basic'].append({"name": "simple", "ctor": "basic"})

        mock_ctor                   = mock_task_ctor()
        mock_ep                     = mock_entry_point(name="basic", value=mock_ctor)

        plugins                     = tomlguard.TomlGuard({"job": [mock_ep]})
        basic                       = task_loader.DootTaskLoader()
        basic.setup(plugins, tomlguard.TomlGuard(specs))

        result    = basic.load()

        assert(len(result) == 1)
        task_spec = result['basic::simple']
        assert(str(task_spec.ctor) == "default:basic")
        assert(task_spec.ctor.value == "basic")



    def test_task_missing_plugin_in(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_sources")
        mocker.patch("doot._configs_loaded_from")
        mocker.patch("importlib.metadata.EntryPoint")
        specs = {"tasks": {"basic": []}}
        specs['tasks']['basic'].append({"name": "simple", "ctor": "bad:not_basic"})

        mock_ep      = importlib.metadata.EntryPoint()
        mock_ep.name = "basic"

        plugins      = tomlguard.TomlGuard({"job": [mock_ep]})
        basic        = task_loader.DootTaskLoader()
        basic.setup(plugins, tomlguard.TomlGuard(specs))

        with pytest.raises(doot.errors.DootTaskLoadError):
            basic.load()


    @pytest.mark.xfail
    def test_task_bad_type_loaded(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_sources")
        mocker.patch("doot._configs_loaded_from")
        mocker.patch("importlib.metadata.EntryPoint")
        specs = {"tasks": {"basic": []}}
        specs['tasks']['basic'].append({"name": "simple", "ctor": "basic"})

        mock_ep      = mock_entry_point()

        plugins      = tomlguard.TomlGuard({"job": [mock_ep]})
        basic        = task_loader.DootTaskLoader()
        basic.setup(plugins, tomlguard.TomlGuard(specs))

        with pytest.raises(doot.errors.DootTaskLoadError):
            basic.load()
