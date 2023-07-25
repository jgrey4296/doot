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
import tomler
import doot
doot.config = tomler.Tomler({})
from doot.loaders import task_loader
logging = logmod.root

class TestTaskLoader:

    def test_initial(self):
        basic = task_loader.DootTaskLoader()
        assert(basic is not None)

    def test_basic__internal_load(self):
        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_tasker::DootTasker"})
        basic = task_loader.DootTaskLoader()
        basic.setup({})
        result = basic._load_raw_specs(tomler.Tomler(specs).tasks, "test_file")

        assert(isinstance(result, list))
        assert(len(result) == 1)
        assert(result[0]['name'] == "test")

    def test_basic_load(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_path")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": {"basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_tasker::DootTasker"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)
        result = basic.load()

        assert(isinstance(result, tomler.Tomler))
        assert(len(result) == 1)
        assert("test" in result)
        assert(isinstance(result['test'][0], dict))
        assert(isinstance(result['test'][1], type))

    def test_multi_load(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_path")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_tasker::DootTasker"})
        specs['tasks']['basic'].append({"name"  : "other", "class": "doot.task.base_tasker::DootTasker"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)
        result = basic.load()

        assert(isinstance(result, tomler.Tomler))
        assert(len(result) == 2)
        assert("test" in result)
        assert("other" in result)

    def test_name_disallow_overload(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_path")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_tasker::DootTasker"})
        specs['tasks']['basic'].append({"name"  : "test", "class": "doot.task.base_tasker::DootTasker"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)
        task_loader.allow_overloads = False

        with pytest.raises(doot.errors.DootTaskLoadError):
            basic.load()

    def test_name_allow_overload(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_path")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": { "basic": []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_tasker::DootTasker"})
        specs['tasks']['basic'].append({"name"  : "test", "class": "doot.task.base_tasker::DootTasker"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, tomler.Tomler(specs))
        task_loader.allow_overloads = True

        result = basic.load()
        assert("test" in result)

    def test_cmd_name_conflict(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_path")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_tasker::DootTasker"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)
        basic.cmd_names = set(["test"])

        with pytest.raises(doot.errors.DootTaskLoadError):
            basic.load()

    def test_bad_task_class(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_path")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": { "basic": []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.base_tasker::DoesntExistTasker"})

        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)

        with pytest.raises(doot.errors.DootTaskLoadError):
            basic.load()

    def test_bad_task_module(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_path")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test", "class" : "doot.task.doesnt_exist_module::DoesntExistTasker"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)

        with pytest.raises(doot.errors.DootTaskLoadError):
            basic.load()

    def test_bad_spec(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_path")
        mocker.patch("doot._configs_loaded_from")

        specs = {"tasks": { "basic" : []}}
        specs['tasks']['basic'].append({"name"  : "test"})
        basic = task_loader.DootTaskLoader()
        basic.setup({}, specs)

        with pytest.raises(doot.errors.DootTaskLoadError):
            result = basic.load()

    def test_task_type(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_path")
        mocker.patch("doot._configs_loaded_from")
        mocker.patch("importlib.metadata.EntryPoint")
        specs = {"tasks": {"basic": []}}
        specs['tasks']['basic'].append({"name": "simple", "type": "basic"})

        mock_ep      = importlib.metadata.EntryPoint()
        mock_ep.name = "basic"
        mock_ep.load = mocker.MagicMock(return_value=True)

        plugins      = tomler.Tomler({"tasker": [mock_ep]})
        basic        = task_loader.DootTaskLoader()
        basic.setup(plugins, tomler.Tomler(specs))

        result = basic.load()
        assert(len(result) == 1)
        assert(result.simple == ({"name": "simple", "type": "basic", "group": "basic", "source": "(extra)"}, True))


    def test_task_bad_type(self, mocker):
        mocker.patch("doot.loaders.task_loader.task_path")
        mocker.patch("doot._configs_loaded_from")
        mocker.patch("importlib.metadata.EntryPoint")
        specs = {"tasks": {"basic": []}}
        specs['tasks']['basic'].append({"name": "simple", "type": "not_basic"})

        mock_ep      = importlib.metadata.EntryPoint()
        mock_ep.name = "basic"
        mock_ep.load = mocker.MagicMock(return_value=True)

        plugins      = tomler.Tomler({"task": [mock_ep]})
        basic        = task_loader.DootTaskLoader()
        basic.setup(plugins, tomler.Tomler(specs))

        with pytest.raises(doot.errors.DootTaskLoadError):
            basic.load()
