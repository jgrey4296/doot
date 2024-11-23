#!/usr/bin/env python3
"""

"""
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
from doot.control.comptracker.track_registry import TrackRegistry
from doot.control.comptracker.track_network import TrackNetwork
from doot.enums import TaskStatus_e
from doot.utils import mock_gen
from doot.enums import TaskMeta_f

# ##-- end 1st party imports

logging = logmod.root

@pytest.fixture(scope="function")
def network():
    registry = TrackRegistry()
    return TrackNetwork(registry)

class TestTrackerNetwork:

    def test_sanity(self, network):
        assert(isinstance(network, TrackNetwork))

    def test_network_connect_to_root(self, network):
        obj = network
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        obj._registry.register_spec(spec)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        assert(bool(obj.pred[obj._root_node]))
        assert(bool(obj.succ[instance]))

    def test_connect_task(self, network):
        obj = network
        name1 = doot.structs.TaskName.build("basic::task").instantiate()
        name2 = doot.structs.TaskName.build("basic::other").instantiate()
        # Mock the specs:
        obj._registry.specs[name1] = True
        obj._registry.specs[name2] = True

        assert(len(obj) == 1)
        obj.connect(name1, name2)
        assert(len(obj) == 3)
        assert(name1 in obj)
        assert(name2 in obj)
        assert(name2 in obj.succ[name1])
        assert(name1 in obj.pred[name2])

    def test_connect_idempotent(self, network):
        obj = network
        name1 = doot.structs.TaskName.build("basic::task").instantiate()
        name2 = doot.structs.TaskName.build("basic::other").instantiate()
        # Mock the tasks:
        obj._registry.specs[name1] = True
        obj._registry.specs[name2] = True
        obj.connect(name1, name2)
        assert(len(obj.succ[name1]) == 1)
        assert(len(obj.pred[name2]) == 1)
        obj.connect(name1, name2)
        assert(len(obj.succ[name1]) == 1)
        assert(len(obj.pred[name2]) == 1)

    def test_connect_tasks_must_be_instanced(self, network):
        obj = network
        name1 = doot.structs.TaskName.build("basic::task")
        name2 = doot.structs.TaskName.build("basic::other")
        # Mock the specs:
        obj._registry.specs[name1] = True
        obj._registry.specs[name2] = True

        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.connect(name1, name2)

    def test_connect_artifact(self, network):
        obj      = network
        name1    = doot.structs.TaskName.build("basic::task").instantiate()
        artifact = doot.structs.TaskArtifact.build("a/simple/artifact.txt")
        # Mock the task/artifact:
        obj._registry.specs[name1] = True
        obj._registry.artifacts[artifact] = []

        assert(len(obj) == 1)
        obj.connect(name1, artifact)
        assert(len(obj) == 3)
        assert(name1 in obj)
        assert(artifact in obj)
        assert(artifact in obj.succ[name1])
        assert(name1 in obj.pred[artifact])

    def test_connect_fail_no_artifact(self, network):
        obj      = network
        name1    = doot.structs.TaskName.build("basic::task").instantiate()
        artifact = doot.structs.TaskArtifact.build("a/simple/artifact.txt")
        # Mock the task/artifact:
        obj._registry.specs[name1] = True
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.connect(name1, artifact)

    def test_connect_fail_no_tasks(self, network):
        obj = network
        name1 = doot.structs.TaskName.build("basic::task").instantiate()
        name2 = doot.structs.TaskName.build("basic::other").instantiate()
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.connect(name1, name2)

    def test_network_retrieval(self, network):
        obj = network
        name1 = doot.structs.TaskName.build("basic::task").instantiate()
        name2 = doot.structs.TaskName.build("basic::other").instantiate()
        # Mock the tasks:
        obj._registry.specs[name1] = True
        obj._registry.specs[name2] = True
        obj.connect(name1, name2)
        assert(name2 in obj.succ[name1])
        assert(name1 in obj.pred[name2])

    def test_concrete_edges(self, network):
        obj   = network
        spec  = doot.structs.TaskSpec.build({
            "name":"basic::task",
            "depends_on":[{"task":"basic::dep", "inject":{"now": {"test_key":"test_key"}}}],
            "required_for": ["basic::chained"],
            "test_key": "bloo"
                                            })
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "depends_on": [{"task":"basic::chained", "inject":{"now":{"test_key":"test_key"}}}], "test_key": "blah"})
        spec3 = doot.structs.TaskSpec.build({"name":"basic::chained"})
        obj._registry.register_spec(spec, spec2, spec3)
        instance = obj._registry._instantiate_spec(spec.name)
        obj.connect(instance)
        obj.build_network()
        result = obj.concrete_edges(instance)
        assert(isinstance(result, TomlGuard))
        assert(bool(result.pred.tasks))
        assert(spec2.name < result.pred.tasks[0])
        assert(bool(result.succ.tasks))
        assert(any(spec3.name < x for x in result.succ.tasks))
        assert(result.root is True)

class TestTrackerNetworkBuild:

    def test_build_empty(self, network):
        obj = network
        assert(len(obj) == 1)
        assert(not bool(obj._registry.tasks))
        assert(not bool(obj._registry.specs))
        assert(not obj.is_valid)
        obj.build_network()
        assert(len(obj) == 1)
        assert(obj.is_valid)

    def test_build_task(self, network):
        """ a simple task, should also have a ..$cleanup$ successor """
        obj = network
        spec = doot.structs.TaskSpec.build({"name":"basic::task"})
        obj._registry.register_spec(spec)
        assert(len(obj) == 1) # Root node
        assert(len(obj._registry.specs) == 2)
        assert(not bool(obj.adj[obj._root_node]))
        instance = obj._registry._instantiate_spec(spec.name)
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 3)
        assert(instance in obj)
        cleanup_instance = obj._registry.concrete[instance.cleanup_name()][0]
        assert(cleanup_instance in obj.succ[instance])


    def test_build_single_dependency_node(self, network):
        obj = network
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["basic::dep"]})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj._registry.register_spec(spec, spec2)
        assert(len(obj) == 1)
        assert(len(obj._registry.specs) == 4)
        assert(not bool(obj.adj[obj._root_node]))
        instance = obj._registry._instantiate_spec(spec.name)
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 5)
        assert(obj._registry.concrete[spec2.name][0] in obj.pred[instance])
        assert(instance in obj.succ[obj._registry.concrete[spec2.name][0]])

    def test_build_single_dependent_node(self, network):
        obj = network
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "required_for":["basic::req"]})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::req"})
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 5)
        assert(obj._registry.concrete[spec2.name][0] in obj.succ[instance])
        assert(instance in obj.pred[obj._registry.concrete[spec2.name][0]])

    def test_build_cleanup_task_empty(self, network):
        obj = network
        spec  = doot.structs.TaskSpec.build({"name":"basic::task"})
        obj._registry.register_spec(spec)
        instance = obj._registry._instantiate_spec(spec.name)
        instance_cleanup = instance.cleanup_name()
        assert(len(obj) == 1)
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 3)

    def test_build_dep_chain(self, network):
        """Check basic::task triggers basic::dep, which triggers basic::chained"""
        obj = network
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["basic::dep"]})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "depends_on":["basic::chained"]})
        spec3 = doot.structs.TaskSpec.build({"name":"basic::chained"})
        obj._registry.register_spec(spec, spec2, spec3)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        obj.validate_network()
        assert(len(obj) == 7)
        assert(obj._registry.concrete[spec2.name][0] in obj.pred[instance])
        assert(obj._registry.concrete[spec3.name][0] in obj.pred[obj._registry.concrete[spec2.name][0]])

class TestTrackerNetworkBuildConstraints:

    def test_build_dep_match_no_constraints(self, network):
        obj = network
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "constraints":False}], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "test_key": "blah"})
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        obj.validate_network()
        assert(len(obj) == 5)
        assert(obj._registry.concrete[spec2.name][0] in obj.pred[instance])

    def test_build_dep_match_with_constraint(self, network):
        obj = network
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "constraints":["test_key"]}], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "test_key": "bloo"})
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 5)
        pred = next(iter(obj.pred[instance]))
        assert(spec2.name  < pred)
        assert(spec.test_key == obj._registry.specs[pred].test_key)

    def test_build_dep_match_with_constraint_fail(self, network):
        obj = network
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "constraints":["test_key"]}], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "test_key": "blah"})
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.build_network()

    def test_build_dep_match_with_injection(self, network):
        obj = network
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "inject":{"now":{"inj_key":"test_key"}}}], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 5)
        pred = list(obj.pred[instance])[0]
        assert(spec2.name  < pred)
        assert(spec.test_key == obj._registry.specs[pred].inj_key)

    def test_build_dep_match_with_injection_fail(self, network):
        obj = network
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "inject":{"now":{"inj_key":"bad_key"}}}], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep"})
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        with pytest.raises(doot.errors.DootTaskTrackingError):
            obj.build_network()

    def test_build_dep_chain_transitive_injection(self, network):
        """
          check a inject can be chained.
          test_key=bloo should be carried from basic::task to basic::dep to basic::chained
        """
        obj = network
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "inject":{"now":["test_key"]}}], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "depends_on": [{"task":"basic::chained", "inject":{"now":["test_key"]}}], "test_key": "blah"})
        spec3 = doot.structs.TaskSpec.build({"name":"basic::chained", "test_key": "aweg"})
        obj._registry.register_spec(spec, spec2, spec3)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 7)
        pred1 = list(obj.pred[instance])[0]
        assert(spec2.name  < pred1)
        assert(spec.test_key == obj._registry.specs[pred1].test_key)
        assert(obj._registry.specs[pred1].sources[-1] == spec2.name)
        assert(obj._registry.specs[pred1].test_key != spec2.test_key)

        pred2 = list(obj.pred[pred1])[0]
        assert(spec3.name  < pred2)
        assert(spec.test_key == obj._registry.specs[pred2].test_key)
        assert(obj._registry.specs[pred2].sources[-1] == spec3.name)
        assert(obj._registry.specs[pred2].test_key != spec3.test_key)

    def test_build_req_chain_with_transitive_injections(self, network):
        """ Construct a requirement, rather than dependency, chain,
          passing the injection up the chain
          """
        obj = network
        # Abstract specs
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "required_for":[{"task":"basic::req", "inject":{"now": ["test_key"]}}], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::req", "required_for": [{"task":"basic::chained", "inject":{"now": ["test_key"]}}]})
        spec3 = doot.structs.TaskSpec.build({"name":"basic::chained"})
        obj._registry.register_spec(spec, spec2, spec3)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 7)
        assert(any(spec2.name  < x for x in obj.succ[instance]))
        # Test concrete specs have carried the injection:
        assert(obj._registry.specs[obj._registry.concrete[spec2.name][0]].test_key == spec.test_key)
        assert(obj._registry.specs[obj._registry.concrete[spec3.name][0]].test_key == spec.test_key)

class TestTrackerNetworkBuildJobs:

    def test_build_job(self, network):
        """ a job should build a ..$head$ as well,
        and the head should build a ..$cleanup$ """
        obj = network
        spec = doot.structs.TaskSpec.build({"name":"basic::job", "flags": ["JOB"]})
        obj._registry.register_spec(spec)
        assert(len(obj) == 1) # Root node
        assert(len(obj._registry.specs) == 3)
        assert(not bool(obj.adj[obj._root_node]))
        instance = obj._registry._instantiate_spec(spec.name)
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 4)
        assert(instance in obj)
        head_instance = obj._registry.concrete[instance.job_head()][0]
        cleanup_instance = obj._registry.concrete[head_instance.cleanup_name()][0]
        assert(head_instance in  obj.succ[instance])
        assert(cleanup_instance in obj.succ[head_instance])

    def test_build_with_head_dep(self, network):
        obj = network
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["basic::job..$head$"], "test_key": "bloo"})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::job", "flags": ["JOB"]})
        assert(TaskMeta_f.JOB in spec2.name)
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(spec.name in obj._registry.concrete)
        assert(spec2.name.job_head() in obj._registry.concrete)
        assert(spec2.name in obj._registry.concrete)
        obj.validate_network()

class TestTrackerNetworkBuildArtifacts:

    def test_build_dep_chain_with_artifact(self, network):
        """check basic::task triggers basic::dep via the intermediary of the artifact test.blah"""
        obj = network
        spec = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["file:>test.blah"]})
        spec2 = doot.structs.TaskSpec.build({"name":"basic::dep", "required_for":["file:>test.blah"]})
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        obj.validate_network()
        assert(len(obj) == 6)
        # Check theres a path between the specs, via the artifact
        assert(nx.has_path(obj._graph, obj._registry.concrete[spec2.name][0], instance))

    def test_build_with_concrete_artifact(self, network):
        obj = network
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["file:>basic.txt"]})
        obj._registry.register_spec(spec)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(len(obj._registry.artifacts) == 1)
        obj.connect(instance)
        obj.build_network()
        assert(spec.depends_on[0].target in obj.pred[instance])
        assert(instance in obj.succ[spec.depends_on[0].target])

    def test_build_with_concrete_artifact(self, network):
        obj = network
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "required_for":["file:>basic.txt"]})
        obj._registry.register_spec(spec)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(len(obj._registry.artifacts) == 1)
        obj.connect(instance)
        obj.build_network()
        assert(spec.required_for[0].target in obj.succ[instance])
        assert(instance in obj.pred[spec.required_for[0].target])

    def test_build_with_abstract_artifact(self, network):
        obj = network
        spec  = doot.structs.TaskSpec.build({"name":"basic::task", "depends_on":["file:>*.txt"]})
        obj._registry.register_spec(spec)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(len(obj._registry.artifacts) == 1)
        obj.connect(instance)
        obj.build_network()
        assert(spec.depends_on[0].target in obj.pred[instance])

    def test_build_artifact_chain(self, network):
        obj = network
        consumer     = doot.structs.TaskSpec.build({"name":"basic::consumer", "depends_on":["file:>*.txt"]})
        producer     = doot.structs.TaskSpec.build({"name":"basic::producer", "required_for":["file:>blah.txt"]})
        dep_artifact = consumer.depends_on[0].target
        req_artifact = producer.required_for[0].target
        obj._registry.register_spec(consumer, producer)
        prod = obj._registry._instantiate_spec(producer.name)
        con  = obj._registry._instantiate_spec(consumer.name)
        assert(len(obj._registry.artifacts) == 2)
        obj.connect(con)
        obj.build_network()
        obj.validate_network()
        # check _registry.artifacts are in network:
        assert(req_artifact in obj)
        assert(dep_artifact in obj)
        # check the tasks are in network:
        assert(con in obj)
        assert(prod in obj)
        # Check chain: consumer <- abstract <- concrete <- producer
        assert(dep_artifact in obj.pred[con])
        # Check the concrete connects to the abstract:
        assert(req_artifact in obj.pred[dep_artifact])
        assert(req_artifact in obj.succ[prod])

class TestTrackerNetworkBuildTransformers:

    def test_build_transformer_from_product_artifact(self, network):
        """ connects a loose source to a transformer, to a product"""
        obj = network
        transformer                     = doot.structs.TaskSpec.build({"name":"basic::transformer", "flags":"TRANSFORMER", "depends_on": ["file:>?.txt"], "required_for": ["file:>?.blah"]})
        concrete_product                = doot.structs.TaskArtifact.build(pl.Path("example.blah"))
        concrete_source                 = doot.structs.TaskArtifact.build(pl.Path("example.txt"))
        obj._registry.register_spec(transformer)
        assert(transformer.name in obj._registry.specs)
        obj._registry._register_artifact(concrete_product)
        obj.connect(concrete_product, None)
        obj.build_network()
        assert(bool(obj._registry.concrete[transformer.name]))
        transformer_instance = obj._registry.concrete[transformer.name][0]
        assert(transformer_instance in obj.pred[concrete_product])
        assert(transformer_instance in obj.succ[concrete_source])


    def test_build_transformer_from_source_artifact(self, network):
        """ connects a loose source to a transformer, to a product"""
        obj = network
        transformer                     = doot.structs.TaskSpec.build({"name":"basic::transformer", "flags":"TRANSFORMER", "depends_on": ["file:>?.txt"], "required_for": ["file:>?.blah"]})
        concrete_product                = doot.structs.TaskArtifact.build(pl.Path("example.blah"))
        concrete_source                 = doot.structs.TaskArtifact.build(pl.Path("example.txt"))
        obj._registry.register_spec(transformer)
        assert(transformer.name in obj._registry.specs)
        obj._registry._register_artifact(concrete_source)
        obj.connect(concrete_source)
        obj.build_network()
        assert(bool(obj._registry.concrete[transformer.name]))
        transformer_instance = obj._registry.concrete[transformer.name][0]
        assert(transformer_instance in obj.pred[concrete_product])
        assert(transformer_instance in obj.succ[concrete_source])

    def test_build_multi_transformers(self, network):
        obj = network
        transformer                     = doot.structs.TaskSpec.build({"name":"basic::transformer", "flags":"TRANSFORMER", "depends_on": ["file:>?.txt"], "required_for": ["file:>?.blah"]})
        concrete_product                = doot.structs.TaskArtifact.build(pl.Path("example.blah"))
        concrete_source                 = doot.structs.TaskArtifact.build(pl.Path("example.txt"))
        concrete_product2                = doot.structs.TaskArtifact.build(pl.Path("aweg.blah"))
        concrete_source2                 = doot.structs.TaskArtifact.build(pl.Path("aweg.txt"))
        obj._registry.register_spec(transformer)
        assert(transformer.name in obj._registry.specs)
        obj._registry._register_artifact(concrete_product)
        obj._registry._register_artifact(concrete_source2)
        obj.connect(concrete_product, None)
        obj.connect(concrete_source2, None)
        obj.build_network()
        assert(len(obj._registry.concrete[transformer.name]) == 2)
        instances = obj._registry.concrete[transformer.name]
        if concrete_source in obj.pred[instances[0]]:
            assert(concrete_product in obj.succ[instances[0]])
            assert(concrete_source2 in obj.pred[instances[1]])
            assert(concrete_product2 in obj.succ[instances[1]])
        else:
            assert(concrete_source in obj.pred[instances[1]])
            assert(concrete_product in obj.succ[instances[1]])
            assert(concrete_source2 in obj.pred[instances[0]])
            assert(concrete_product2 in obj.succ[instances[0]])
