#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import unittest
import warnings
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

logging = logmod.root

# ##-- stdlib imports
from uuid import UUID

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
from tomlguard import TomlGuard
import networkx as nx

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
doot._test_setup()
import doot.errors
import doot.structs
from doot._abstract import Task_i
from doot.control.base_tracker import BaseTracker
from doot.control.tracker import DootTracker
from doot.enums import TaskStatus_e
from doot.utils import mock_gen

# ##-- end 1st party imports

class TestTrackerStore:

    def test_basic(self):
        obj = BaseTracker()
        assert(obj is not None)

    def test_register_spec(self):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        assert(not bool(obj.specs))
        obj.register_spec(spec)
        assert(bool(obj.specs))


    def test_register_job_spec(self):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "ctor":"doot.task.base_job:DootJob"})
        assert(not bool(obj.specs))
        obj.register_spec(spec)
        assert(bool(obj.specs))
        assert(spec.name in obj.specs)
        assert(spec.name.job_head() in obj.specs)
        conc_spec = obj.concrete[spec.name][0]
        assert(conc_spec.job_head() not in obj.specs)


    def test_register_spec_instantiates(self):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        assert(not bool(obj.specs))
        assert(not bool(obj.concrete[spec.name]))
        obj.register_spec(spec)
        assert(bool(obj.specs))
        assert(bool(obj.concrete[spec.name]))


    def test_register_is_idempotent(self):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        assert(not bool(obj.specs))
        assert(not bool(obj.concrete[spec.name]))
        for i in range(5):
            obj.register_spec(spec)
            assert(len(obj.specs) == 2)
            assert(len(obj.concrete[spec.name]) == 1)

    def test_register_spec_with_artifacts(self):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["file:>test.txt"], "required_for": ["file:>other.txt"]})
        assert(not bool(obj.artifacts))
        obj.register_spec(spec)
        assert(bool(obj.artifacts))


    def test_register_spec_ignores_disabled(self):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "disabled":True})
        assert(len(obj.specs) == 0)
        obj.register_spec(spec)
        assert(len(obj.specs) == 0)

    def test_register_transformer_spec(self):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::transformer", "flags":"TRANSFORMER", "depends_on": ["file:>?.txt"], "required_for": ["file:>?.blah"]})
        assert(len(obj.specs) == 0)
        assert(len(obj._transformer_specs) == 0)
        obj.register_spec(spec)
        assert(len(obj.specs) == 1)
        assert(len(obj._transformer_specs) == 2)
        assert("?.txt" in obj._transformer_specs)
        assert("?.blah" in obj._transformer_specs)

    def test_spec_retrieval(self):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        retrieved = obj.specs[name]
        assert(retrieved == spec)

    def test_make_task(self, mocker):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        # Mock entry in network:
        obj.network.add_node(instance)
        assert(not bool(obj.tasks))
        obj._make_task(instance)
        assert(bool(obj.tasks))

    def test_task_retrieval(self):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        # Mock entry in network:
        obj.network.add_node(instance)
        result = obj._make_task(instance)
        retrieved = obj.tasks[result]
        assert(isinstance(retrieved, Task_i))

    def test_task_get_default_status(self):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        # Mock entry in network:
        obj.network.add_node(instance)
        result   = obj._make_task(instance)
        status   = obj.get_status(result)
        assert(status is TaskStatus_e.default)

    def test_task_status_missing_task(self):
        obj = BaseTracker()
        name = doot.structs.TaskName.build("basic::task")
        assert(obj.get_status(name) == TaskStatus_e.NAMED)

    def test_set_status(self):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        name = spec.name
        obj.register_spec(spec)
        instance = obj._instantiate_spec(name)
        # Mock entry in network:
        obj.network.add_node(instance)
        result = obj._make_task(instance)
        assert(obj.get_status(result) is TaskStatus_e.default)
        assert(obj.set_status(result, TaskStatus_e.SUCCESS) is True)
        assert(obj.get_status(result) is TaskStatus_e.SUCCESS)

    def test_set_status_missing_task(self):
        obj = BaseTracker()
        name = doot.structs.TaskName.build("basic::task")
        assert(obj.set_status(name, TaskStatus_e.SUCCESS) is False)

class TestTrackerNetwork:

    def test_network_connect_to_root(self):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        assert(bool(obj.network.pred[obj._root_node]))
        assert(bool(obj.network.succ[instance]))

    def test_connect_task(self):
        obj = BaseTracker()
        name1 = doot.structs.TaskName.build("basic::task").instantiate()
        name2 = doot.structs.TaskName.build("basic::other").instantiate()
        # Mock the specs:
        obj.specs[name1] = True
        obj.specs[name2] = True

        assert(len(obj.network) == 1)
        obj.connect(name1, name2)
        assert(len(obj.network) == 3)
        assert(name1 in obj.network)
        assert(name2 in obj.network)
        assert(name2 in obj.network.succ[name1])
        assert(name1 in obj.network.pred[name2])

    def test_connect_artifact(self):
        obj      = BaseTracker()
        name1    = doot.structs.TaskName.build("basic::task").instantiate()
        artifact = doot.structs.TaskArtifact.build("a/simple/artifact.txt")
        # Mock the task/artifact:
        obj.specs[name1] = True
        obj.artifacts[artifact] = []

        assert(len(obj.network) == 1)
        obj.connect(name1, artifact)
        assert(len(obj.network) == 3)
        assert(name1 in obj.network)
        assert(artifact in obj.network)
        assert(artifact in obj.network.succ[name1])
        assert(name1 in obj.network.pred[artifact])

    def test_connect_fail_no_artifact(self):
        obj      = BaseTracker()
        name1    = doot.structs.TaskName.build("basic::task").instantiate()
        artifact = doot.structs.TaskArtifact.build("a/simple/artifact.txt")
        # Mock the task/artifact:
        obj.specs[name1] = True
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.connect(name1, artifact)

    def test_connect_fail_no_tasks(self):
        obj = BaseTracker()
        name1 = doot.structs.TaskName.build("basic::task").instantiate()
        name2 = doot.structs.TaskName.build("basic::other").instantiate()
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.connect(name1, name2)

    def test_network_retrieval(self):
        obj = BaseTracker()
        name1 = doot.structs.TaskName.build("basic::task").instantiate()
        name2 = doot.structs.TaskName.build("basic::other").instantiate()
        # Mock the tasks:
        obj.specs[name1] = True
        obj.specs[name2] = True
        obj.connect(name1, name2)
        assert(name2 in obj.network.succ[name1])
        assert(name1 in obj.network.pred[name2])

    def test_connect_idempotent(self):
        obj = BaseTracker()
        name1 = doot.structs.TaskName.build("basic::task").instantiate()
        name2 = doot.structs.TaskName.build("basic::other").instantiate()
        # Mock the tasks:
        obj.specs[name1] = True
        obj.specs[name2] = True
        obj.connect(name1, name2)
        assert(len(obj.network.succ[name1]) == 1)
        assert(len(obj.network.pred[name2]) == 1)
        obj.connect(name1, name2)
        assert(len(obj.network.succ[name1]) == 1)
        assert(len(obj.network.pred[name2]) == 1)

class TestTrackerNetworkBuild:

    def test_build_empty(self):
        obj = BaseTracker()
        assert(len(obj.network) == 1)
        assert(not bool(obj.tasks))
        assert(not bool(obj.specs))
        assert(not obj.network_is_valid)
        obj.build_network()
        assert(len(obj.network) == 1)
        assert(obj.network_is_valid)

    def test_build_single_dependency_node(self):
        obj  = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["basic::dep"]})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, spec2)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        instance = obj._instantiate_spec(spec.name)
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(len(obj.network) == 3)
        assert(obj.concrete[spec2.name][0] in obj.network.pred[instance])
        assert(instance in obj.network.succ[obj.concrete[spec2.name][0]])

    def test_build_single_dependent_node(self):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "required_for":["basic::req"]})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::req"})
        obj.register_spec(spec, spec2)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(len(obj.network) == 3)
        assert(obj.concrete[spec2.name][0] in obj.network.succ[instance])
        assert(instance in obj.network.pred[obj.concrete[spec2.name][0]])


    def test_build_dep_chain(self):
        """Check basic::task triggers basic::dep, which triggers basic::chained"""
        obj  = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["basic::dep"]})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "depends_on":["basic::chained"]})
        spec3 = doot.structs.TaskSpec.build({"name":"basic::chained"})
        obj.register_spec(spec, spec2, spec3)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        obj.validate_network()
        assert(len(obj.network) == 4)
        assert(obj.concrete[spec2.name][0] in obj.network.pred[instance])
        assert(obj.concrete[spec3.name][0] in obj.network.pred[obj.concrete[spec2.name][0]])


    def test_build_dep_chain_with_artifact(self):
        """check basic::task triggers basic::dep via the intermediary of the artifact test.blah"""
        obj  = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["file:>test.blah"]})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "required_for":["file:>test.blah"]})
        obj.register_spec(spec, spec2)
        instance = obj.queue_entry(spec.name)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        obj.validate_network()
        assert(len(obj.network) == 4)
        # Check theres a path between the specs, via the artifact
        assert(nx.has_path(obj.network, obj.concrete[spec2.name][0], instance))

    def test_build_dep_match_no_constraints(self):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "constraints":[]}], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "test_key": "blah"})
        obj.register_spec(spec, spec2)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        obj.validate_network()
        assert(len(obj.network) == 3)
        assert(obj.concrete[spec2.name][0] in obj.network.pred[instance])

    def test_build_dep_match_with_constraint(self):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "constraints":["test_key"]}], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "test_key": "bloo"})
        obj.register_spec(spec, spec2)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(len(obj.network) == 3)
        pred = list(obj.network.pred[instance])[0]
        assert(spec2.name  < pred)
        assert(spec.test_key == obj.specs[pred].test_key)

    def test_build_dep_match_with_constraint_fail(self):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "constraints":["test_key"]}], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "test_key": "blah"})
        obj.register_spec(spec, spec2)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.build_network()

    def test_build_dep_match_with_injection(self):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "injections":{"inj_key":"test_key"}}], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, spec2)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(len(obj.network) == 3)
        pred = list(obj.network.pred[instance])[0]
        assert(spec2.name  < pred)
        assert(spec.test_key == obj.specs[pred].inj_key)


    def test_build_dep_match_with_injection_fail(self):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "injections":{"inj_key":"bad_key"}}], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj.register_spec(spec, spec2)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.build_network()

    def test_build_dep_chain_transitive_injection(self):
        """
          check a injections can be chained.
          test_key=bloo should be carried from basic::task to basic::dep to basic::chained
        """
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "injections":{"test_key":"test_key"}}], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "depends_on": [{"task":"basic::chained", "injections":{"test_key":"test_key"}}], "test_key": "blah"})
        spec3 = doot.structs.TaskSpec.build({"name":"basic::chained", "test_key": "aweg"})
        obj.register_spec(spec, spec2, spec3)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(len(obj.network) == 4)
        pred1 = list(obj.network.pred[instance])[0]
        assert(spec2.name  < pred1)
        assert(spec.test_key == obj.specs[pred1].test_key)
        assert(obj.specs[pred1].sources[-1] == spec2.name)
        assert(obj.specs[pred1].test_key != spec2.test_key)

        pred2 = list(obj.network.pred[pred1])[0]
        assert(spec3.name  < pred2)
        assert(spec.test_key == obj.specs[pred2].test_key)
        assert(obj.specs[pred2].sources[-1] == spec3.name)
        assert(obj.specs[pred2].test_key != spec3.test_key)

    def test_build_req_chain_with_transitive_injections(self):
        """ Construct a requirement, rather than dependency, chain,
          passing the injection up the chain
          """
        obj   = BaseTracker()
        # Abstract specs
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "required_for":[{"task":"basic::req", "injections":{"test_key":"test_key"}}], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::req", "required_for": [{"task":"basic::chained", "injections":{"test_key":"test_key"}}]})
        spec3 = doot.structs.TaskSpec.build({"name":"basic::chained"})
        obj.register_spec(spec, spec2, spec3)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(len(obj.network) == 4)
        succ1 = [x for x in obj.network.succ[instance] if x != obj._root_node][0]
        assert(spec2.name  < succ1)
        # Test concrete specs have carried the injection:
        assert(obj.specs[obj.concrete[spec2.name][1]].test_key == spec.test_key)
        assert(obj.specs[obj.concrete[spec3.name][1]].test_key == spec.test_key)


    def test_build_with_head_dep(self):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["basic::dep..$head$"], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "flags": ["JOB"]})
        obj.register_spec(spec, spec2)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        assert(spec.name in obj.concrete)
        assert(spec2.name.job_head() in obj.concrete)
        assert(spec2.name in obj.concrete)
        obj.validate_network()

    def test_build_with_concrete_artifact(self):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["file:>basic.txt"]})
        obj.register_spec(spec)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(len(obj.artifacts) == 1)
        obj.connect(instance)
        obj.build_network()
        assert(spec.depends_on[0].target in obj.network.pred[instance])
        assert(instance in obj.network.succ[spec.depends_on[0].target])

    def test_build_with_concrete_artifact(self):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "required_for":["file:>basic.txt"]})
        obj.register_spec(spec)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(len(obj.artifacts) == 1)
        obj.connect(instance)
        obj.build_network()
        assert(spec.required_for[0].target in obj.network.succ[instance])
        assert(instance in obj.network.pred[spec.required_for[0].target])

    def test_build_with_abstract_artifact(self):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["file:>*.txt"]})
        obj.register_spec(spec)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(len(obj.artifacts) == 1)
        obj.connect(instance)
        obj.build_network()
        assert(spec.depends_on[0].target in obj.network.pred[instance])

    def test_build_artifact_chain(self):
        obj          = BaseTracker()
        consumer     = doot.structs.TaskSpec.build({"name":"basic::consumer", "depends_on":["file:>*.txt"]})
        producer     = doot.structs.TaskSpec.build({"name":"basic::producer", "required_for":["file:>blah.txt"]})
        dep_artifact = consumer.depends_on[0].target
        req_artifact = producer.required_for[0].target
        obj.register_spec(consumer, producer)
        prod = obj._instantiate_spec(producer.name)
        con  = obj._instantiate_spec(consumer.name)
        assert(len(obj.artifacts) == 2)
        obj.connect(con)
        obj.build_network()
        obj.validate_network()
        # check artifacts are in network:
        assert(req_artifact in obj.network)
        assert(dep_artifact in obj.network)
        # check the tasks are in network:
        assert(con in obj.network)
        assert(prod in obj.network)
        # Check chain: consumer <- abstract <- concrete <- producer
        assert(dep_artifact in obj.network.pred[con])
        # Check the concrete connects to the abstract:
        assert(req_artifact in obj.network.pred[dep_artifact])
        assert(req_artifact in obj.network.succ[prod])

    def test_build_transformer_from_artifact(self):
        obj                             = BaseTracker()
        transformer                     = doot.structs.TaskSpec.build({"name":"basic::task", "flags":"TRANSFORMER", "depends_on": ["file:>?.txt"], "required_for": ["file:>?.blah"]})
        concrete_product                = doot.structs.TaskArtifact.build(pl.Path("example.blah"))
        concrete_source                 = doot.structs.TaskArtifact.build(pl.Path("example.txt"))
        obj.artifacts[concrete_product] = []
        obj.artifacts[concrete_source]  = []
        obj.register_spec(transformer)
        assert(transformer.name in obj.specs)
        obj.connect(concrete_product, None)
        obj.connect(concrete_source, False)
        obj.build_network()
        assert(bool(obj.concrete[transformer.name]))
        transformer_instance = obj.concrete[transformer.name][0]
        assert(transformer_instance in obj.network.pred[concrete_product])
        assert(transformer_instance in obj.network.succ[concrete_source])

    def test_build_multi_transformers(self):
        obj                             = BaseTracker()
        transformer                     = doot.structs.TaskSpec.build({"name":"basic::task", "flags":"TRANSFORMER", "depends_on": ["file:>?.txt"], "required_for": ["file:>?.blah"]})
        concrete_product                = doot.structs.TaskArtifact.build(pl.Path("example.blah"))
        concrete_source                 = doot.structs.TaskArtifact.build(pl.Path("example.txt"))
        concrete_product2                = doot.structs.TaskArtifact.build(pl.Path("aweg.blah"))
        concrete_source2                 = doot.structs.TaskArtifact.build(pl.Path("aweg.txt"))
        obj.artifacts[concrete_product] = []
        obj.artifacts[concrete_source]  = []
        obj.artifacts[concrete_product2] = []
        obj.artifacts[concrete_source2]  = []
        obj.register_spec(transformer)
        assert(transformer.name in obj.specs)
        obj.connect(concrete_product, None)
        obj.connect(concrete_source, False)
        obj.connect(concrete_product2, None)
        obj.connect(concrete_source2, False)
        obj.build_network()
        assert(len(obj.concrete[transformer.name]) == 2)
        instances = obj.concrete[transformer.name]
        if concrete_source in obj.network.pred[instances[0]]:
            assert(concrete_product in obj.network.succ[instances[0]])
            assert(concrete_source2 in obj.network.pred[instances[1]])
            assert(concrete_product2 in obj.network.succ[instances[1]])
        else:
            assert(concrete_source in obj.network.pred[instances[1]])
            assert(concrete_product in obj.network.succ[instances[1]])
            assert(concrete_source2 in obj.network.pred[instances[0]])
            assert(concrete_product2 in obj.network.succ[instances[0]])

class TestTrackerQueue:

    def test_tracker_bool(self, mocker):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        assert(not bool(obj._queue))
        assert(not bool(obj))
        instance = obj.queue_entry(spec.name)
        assert(bool(obj._queue))
        assert(bool(obj))

    def test_queue_task(self, mocker):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        assert(not bool(obj._queue))
        instance = obj.queue_entry(spec.name)
        assert(instance in obj.active_set)
        assert(bool(obj._queue))


    def test_queue_task_idempotnent(self, mocker):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        assert(not bool(obj._queue))
        instance = obj.queue_entry(spec.name)
        assert(instance in obj.active_set)
        assert(bool(obj._queue))
        assert(len(obj.active_set) == 1)
        instance = obj.queue_entry(spec.name)
        assert(len(obj.active_set) == 1)

    def test_queue_task_fail_when_not_registered(self):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        name1 = doot.structs.TaskName.build("basic::task")
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.queue_entry(name1)

    def test_queue_artifiact(self):
        obj   = BaseTracker()
        artifact = doot.structs.TaskArtifact.build(pl.Path("test.txt"))
        # Stub artifact entry in tracker:
        obj.artifacts[artifact] = []
        obj._add_node(artifact)
        assert(not bool(obj))
        result = obj.queue_entry(artifact)
        assert(bool(obj))
        assert(artifact is result)

    def test_deque_task(self, mocker):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::other"})
        obj.register_spec(spec, spec2)
        instance = obj.queue_entry(spec.name)
        instance2 = obj.queue_entry(spec2.name)
        assert(instance in obj.active_set)
        assert(instance2 in obj.active_set)
        val = obj.deque_entry()
        assert(val == instance)
        assert(instance in obj.active_set)


    def test_deque_artifact(self, mocker):
        obj      = BaseTracker()
        artifact = doot.structs.TaskArtifact.build(pl.Path("test.txt"))
        # stub artifact in tracker:
        obj.artifacts[artifact] = []
        obj._add_node(artifact)
        result   = obj.queue_entry(artifact)
        assert(bool(obj))
        val = obj.deque_entry()
        assert(not bool(obj))
        assert(val is artifact)

    def test_peek_task(self, mocker):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::other"})
        obj.register_spec(spec, spec2)
        instance  = obj.queue_entry(spec.name)
        instance2 = obj.queue_entry(spec2.name)
        assert(instance in obj.active_set)
        assert(instance2 in obj.active_set)
        val = obj.deque_entry(peek=True)
        assert(val == instance)
        assert(instance in obj.active_set)

    def test_clear_queue(self, mocker):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        obj.register_spec(spec)
        instance = obj.queue_entry(spec.name)
        assert(bool(obj.active_set))
        obj.clear_queue()
        assert(not bool(obj.active_set))

class TestTrackerInternals:

    def test_basic(self):
        obj = BaseTracker()
        assert(obj is not None)

    def test_instantiate_spec_no_op(self):
        obj       = BaseTracker()
        base_spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        spec      = doot.structs.TaskSpec.build({"name":"test::spec"})
        obj.register_spec(base_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec is not special)
        assert(spec is not base_spec)
        assert(spec.name < special)
        assert(special in obj.concrete[spec.name])

    def test_instantiate_spec(self):
        obj = BaseTracker()
        base_spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        dep_spec = doot.structs.TaskSpec.build({"name": "example::dep"})
        spec    = doot.structs.TaskSpec.build({"name":"test::spec", "sources": "basic::task", "bloo": 15})
        obj.register_spec(base_spec, dep_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.TaskName))
        assert(special in obj.concrete[spec.name])


    def test_instantiate_spec_match_reuse(self):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        obj.register_spec(spec)
        instances = set()
        for i in range(5):
            instance = obj._instantiate_spec(spec.name)
            assert(isinstance(instance, doot.structs.TaskName))
            assert(instance in obj.concrete[spec.name])
            instances.add(instance)
            assert(spec.name < instance)
            assert(obj.specs[instance] is not obj.specs[spec.name])
            assert(len(obj.concrete[spec.name]) == 1)
        assert(len(instances) == 1)

    def test_instantiate_job_top(self):
        obj = BaseTracker()
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "ctor": "doot.task.base_job:DootJob", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        abs_head = spec.name.job_head()
        obj.register_spec(spec)
        instance = obj._instantiate_spec(spec.name)
        inst_head = instance.job_head()
        assert(instance in obj.specs)
        assert(abs_head in obj.specs)
        assert(instance in obj.concrete[spec.name])
        assert(spec.name < abs_head)
        assert(spec.name < instance)
        assert(instance < inst_head)
        assert(inst_head not in obj.specs)

    def test_instantiate_spec_chain(self):
        obj = BaseTracker()
        base_spec = doot.structs.TaskSpec.build({"name":"basic::task", "blah": 2, "bloo": 5})
        dep_spec = doot.structs.TaskSpec.build({"name": "example::dep", "sources":"basic::task", "bloo":10, "aweg":15 })
        spec    = doot.structs.TaskSpec.build({"name":"test::spec", "sources": "example::dep", "aweg": 20})
        obj.register_spec(base_spec, dep_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.TaskName))

    def test_instantiate_spec_name_change(self):
        obj       = BaseTracker()
        base_spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        dep_spec = doot.structs.TaskSpec.build({"name": "example::dep"})
        spec    = doot.structs.TaskSpec.build({"name":"test::spec", "sources": "basic::task", "bloo": 15})
        obj.register_spec(base_spec, dep_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.TaskName))
        assert(spec.name < special)
        assert(isinstance(special.tail[-1], UUID))

    def test_instantiate_spec_extra_merge(self):
        obj = BaseTracker()
        base_spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"], "blah": 2, "bloo": 5})
        dep_spec = doot.structs.TaskSpec.build({"name": "example::dep"})
        spec    = doot.structs.TaskSpec.build({"name":"test::spec", "sources": "basic::task", "bloo": 15, "aweg": "aweg"})
        obj.register_spec(base_spec, dep_spec, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.TaskName))
        concrete = obj.specs[special]
        assert(concrete.extra.blah == 2)
        assert(concrete.extra.bloo == 15)

    def test_instantiate_spec_depends_merge(self):
        obj = BaseTracker()
        base_spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["example::dep"]})
        dep_spec = doot.structs.TaskSpec.build({"name": "example::dep"})
        dep_spec2 = doot.structs.TaskSpec.build({"name": "another::dep"})
        spec    = doot.structs.TaskSpec.build({"name":"test::spec", "sources": "basic::task", "depends_on":["another::dep"]})
        obj.register_spec(base_spec, dep_spec, dep_spec2, spec)
        special = obj._instantiate_spec(spec.name)
        assert(spec.name < special)
        assert(spec is not base_spec)
        assert(isinstance(special, doot.structs.TaskName))
        concrete = obj.specs[special]
        assert(len(concrete.depends_on) == 2)
        assert(any("example::dep" in x.target for x in concrete.depends_on))
        assert(any("another::dep" in x.target for x in concrete.depends_on))

    def test_concrete_edges(self):
        obj   = BaseTracker()
        spec  = doot.structs.TaskSpec.build({
            "name":"basic::task",
            "depends_on":[{"task":"basic::dep", "injections":{"test_key":"test_key"}}],
            "required_for": ["basic::chained"],
            "test_key": "bloo"
                                            })
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "depends_on": [{"task":"basic::chained", "injections":{"test_key":"test_key"}}], "test_key": "blah"})
        spec3 = doot.structs.TaskSpec.build({"name":"basic::chained"})
        obj.register_spec(spec, spec2, spec3)
        instance = obj._instantiate_spec(spec.name)
        assert(len(obj.network) == 1)
        assert(not bool(obj.network.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj.network) == 2)
        obj.build_network()
        result = obj.concrete_edges(instance)
        assert(isinstance(result, TomlGuard))
        assert(bool(result.pred.tasks))
        assert(spec2.name < result.pred.tasks[0])
        assert(bool(result.succ.tasks))
        assert(spec3.name < result.succ.tasks[0])
        assert(result.root is True)
