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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import pytest
import networkx as nx
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.workflow._interface import TaskStatus_e, TaskMeta_e
from doot.workflow import TaskName
from doot.util import mock_gen

from ..registry import TrackRegistry
from ..network import TrackNetwork

# ##-- end 1st party imports

from doot.workflow import TaskSpec, TaskArtifact

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|
# isort: on
# ##-- end types
#
logging = logmod.root

@pytest.fixture(scope="function")
def network():
    registry = TrackRegistry()
    return TrackNetwork(registry)

##--|

class TestTrackerNetwork:

    def test_sanity(self, network):
        assert(isinstance(network, TrackNetwork))

    def test_network_connect_to_root(self, network):
        obj = network
        spec = TaskSpec.build({"name":"basic::task"})
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
        name1 = TaskName("basic::task").to_uniq()
        name2 = TaskName("basic::other").to_uniq()
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
        name1 = TaskName("basic::task").to_uniq()
        name2 = TaskName("basic::other").to_uniq()
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
        name1 = TaskName("basic::task")
        name2 = TaskName("basic::other")
        # Mock the specs:
        obj._registry.specs[name1] = True
        obj._registry.specs[name2] = True

        with pytest.raises(doot.errors.TrackingError):
            obj.connect(name1, name2)

    def test_connect_artifact(self, network):
        obj      = network
        name1    = TaskName("basic::task").to_uniq()
        artifact = TaskArtifact("file::>a/simple/artifact.txt")
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
        name1    = TaskName("basic::task").to_uniq()
        artifact = TaskArtifact("file::>a/simple/artifact.txt")
        # Mock the task/artifact:
        obj._registry.specs[name1] = True
        with pytest.raises(doot.errors.TrackingError):
            obj.connect(name1, artifact)

    def test_connect_fail_no_tasks(self, network):
        obj = network
        name1 = TaskName("basic::task").to_uniq()
        name2 = TaskName("basic::other").to_uniq()
        with pytest.raises(doot.errors.TrackingError):
            obj.connect(name1, name2)

    def test_network_retrieval(self, network):
        obj = network
        name1 = TaskName("basic::task").to_uniq()
        name2 = TaskName("basic::other").to_uniq()
        # Mock the tasks:
        obj._registry.specs[name1] = True
        obj._registry.specs[name2] = True
        obj.connect(name1, name2)
        assert(name2 in obj.succ[name1])
        assert(name1 in obj.pred[name2])

    def test_concrete_edges(self, network):
        obj   = network
        spec  = TaskSpec.build({
            "name":"basic::task",
            "depends_on":[{"task":"basic::dep", "inject":{"from_spec": {"test_key":"{test_key}"}}}],
            "required_for": ["basic::chained"],
            "test_key": "bloo"
        })
        spec2 = TaskSpec.build({"name":"basic::dep",
                                "depends_on": [{"task":"basic::chained", "inject":{"from_spec":{"test_key":"{test_key}"}}}],
                                })
        spec3 = TaskSpec.build({"name":"basic::chained", "must_inject":["test_key"]})
        obj._registry.register_spec(spec, spec2, spec3)
        instance = obj._registry._instantiate_spec(spec.name)
        obj.connect(instance)
        obj.build_network()
        result = obj.concrete_edges(instance)
        assert(isinstance(result, ChainGuard))
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
        """ $cleanup$ successors are not built till a task is instantiated """
        obj          = network
        spec         = TaskSpec.build({"name":"basic::task"})
        obj._registry.register_spec(spec)
        assert(len(obj) == 1) # Root node
        assert(len(obj._registry.specs) == 1) # Just the spec
        assert(not bool(obj.adj[obj._root_node]))
        instance = obj._registry._instantiate_spec(spec.name)
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 3)
        assert(instance in obj)

    def test_build_cleanup(self, network):
        """ $cleanup$ successors are not built till a task is instantiated """
        obj  = network
        spec = TaskSpec.build({"name":"basic::task"})
        cleanup_name = spec.name.with_cleanup()
        obj._registry.register_spec(spec)
        instance     = obj._registry._instantiate_spec(spec.name)
        obj.connect(instance)
        obj.build_network()
        match obj._registry.concrete.get(cleanup_name, None):
            case [TaskName() as cleanup_inst]:
                cleanup_spec = obj._registry.specs[cleanup_inst]
                assert(cleanup_spec.name.is_cleanup())
                assert(cleanup_name < cleanup_spec.name)
                assert(any(cleanup_name < x for x in obj.succ[instance]))
            case x:
                assert(False), x

    def test_build_single_dependency_node(self, network):
        obj   = network
        spec  = TaskSpec.build({"name":"basic::task", "depends_on":["basic::dep"]})
        spec2 = TaskSpec.build({"name":"basic::dep"})
        obj._registry.register_spec(spec, spec2)
        assert(len(obj) == 1)
        assert(len(obj._registry.specs) == 2)
        assert(not bool(obj.adj[obj._root_node]))
        instance = obj._registry._instantiate_spec(spec.name)
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 5)
        match obj._registry.concrete.get(spec2.name, None):
            case [TaskName() as dep_inst]:
                assert(spec2.name < dep_inst)
                assert(dep_inst in obj.pred[instance])
                assert(instance in obj.succ[dep_inst])

    def test_build_single_dependent_node(self, network):
        obj   = network
        spec  = TaskSpec.build({"name":"basic::task", "required_for":["basic::req"]})
        spec2 = TaskSpec.build({"name":"basic::req"})
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 5)
        match obj._registry.concrete.get(spec2.name, None):
            case [TaskName() as dep_inst]:
                assert(spec2.name < dep_inst)
                assert(dep_inst in obj.succ[instance])
                assert(instance in obj.pred[dep_inst])
            case x:
                assert(False), x

    def test_build_cleanup_task_even_when_empty(self, network):
        obj   = network
        spec  = TaskSpec.build({"name":"basic::task"})
        obj._registry.register_spec(spec)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 3)

    def test_build_dep_chain(self, network):
        """Check basic::task triggers basic::dep, which triggers basic::chained"""
        obj = network
        spec = TaskSpec.build({"name":"basic::task", "depends_on":["basic::dep"]})
        spec2 = TaskSpec.build({"name":"basic::dep", "depends_on":["basic::chained"]})
        spec3 = TaskSpec.build({"name":"basic::chained"})
        obj._registry.register_spec(spec, spec2, spec3)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        obj.validate_network()
        assert(len(obj) == 7)
        match obj._registry.concrete.get(spec2.name, None):
            case [TaskName() as dep_inst]:
                assert(spec2.name < dep_inst)
                assert(dep_inst in obj.pred[instance])
            case x:
                assert(False), x

        match obj._registry.concrete.get(spec3.name, None):
            case [TaskName() as chain_inst]:
                assert(spec3.name < chain_inst)
                assert(chain_inst in obj.pred[dep_inst])
            case x:
                assert(False), x


    @pytest.mark.xfail
    def test_build_separate_dependencies_from_spec(self, network):
        """
        For a task, T, with dependency D,
        T1->D1
        T2->D2

        """
        obj      = network
        relation = {"task":"basic::dep", "inject":{"from_spec":["blah"]}}
        spec     = TaskSpec.build({"name":"basic::task", "depends_on":[relation]})
        dep      = TaskSpec.build({"name":"basic::dep", "must_inject":["blah"]})
        obj._registry.register_spec(spec, dep)
        T1 = obj._registry._instantiate_spec(spec.name, extra={"blah":"bloo"})
        T2 = obj._registry._instantiate_spec(spec.name, extra={"blah":"aweg"})

        obj.connect(T1)
        obj.connect(T2)
        obj.build_network()
        assert(len(obj._registry.concrete["basic::dep"]) == 2)


    def test_build_separate_dependencies_from_state(self, network):
        """
        For a task, T, with dependency D,
        T1->D1
        T2->D2

        """
        obj      = network
        relation = {"task":"basic::dep", "inject":{"from_state":["blah"]}}
        spec     = TaskSpec.build({"name":"basic::task", "depends_on":[relation]})
        dep      = TaskSpec.build({"name":"basic::dep", "must_inject":["blah"]})
        obj._registry.register_spec(spec, dep)
        T1 = obj._registry._instantiate_spec(spec.name, extra={"blah":"bloo"})
        T2 = obj._registry._instantiate_spec(spec.name, extra={"blah":"aweg"})

        obj.connect(T1)
        obj.connect(T2)
        obj.build_network()
        assert(len(obj._registry.concrete["basic::dep"]) == 2)
        for dep in obj._registry.concrete["basic::dep"]:
            assert(len(obj.succ[dep]) == 2)



class TestTrackerNetworkBuild_Constraints:

    def test_build_dep_match_no_constraints(self, network):
        obj = network
        spec  = TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "constraints":False}], "test_key": "bloo"})
        spec2 = TaskSpec.build({"name":"basic::dep", "test_key": "blah"})
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        obj.validate_network()
        assert(len(obj) == 5)
        match obj._registry.concrete.get(spec2.name, None):
            case [TaskName() as dep_inst]:
                assert(spec2.name < dep_inst)
                assert(dep_inst in obj.pred[instance])
            case x:
                assert(False), x

    def test_build_dep_match_with_constraint(self, network):
        obj = network
        spec  = TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "constraints":["test_key"]}], "test_key": "bloo"})
        spec2 = TaskSpec.build({"name":"basic::dep", "test_key": "bloo"})
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 5)
        match list(obj.pred[instance]):
            case [TaskName() as dep_inst]:
                assert(spec2.name < dep_inst)
                assert(spec.test_key == obj._registry.specs[dep_inst].test_key)
            case x:
                assert(False), x

    def test_build_dep_match_with_constraint_fail(self, network):
        obj = network
        relation = {"task":"basic::dep", "constraints":["test_key"]}
        spec  = TaskSpec.build({"name":"basic::task",
                                "depends_on":[relation],
                                "test_key": "bloo"})
        spec2 = TaskSpec.build({"name":"basic::dep", "test_key": "blah"})
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        assert(not bool(obj._registry.concrete[spec2.name]))
        obj.build_network()
        assert(bool(obj._registry.concrete[spec2.name]))

    def test_build_dep_match_with_injection(self, network):
        obj = network
        spec  = TaskSpec.build({"name":"basic::task",
                                "depends_on":[{"task":"basic::dep", "inject":{"from_spec":{"inj_key":"{test_key}"}}}],
                                "test_key": "bloo"})
        spec2 = TaskSpec.build({"name":"basic::dep", "must_inject":["inj_key"]})
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 5)
        match list(obj.pred[instance]):
            case [TaskName() as dep_inst]:
                dep_inst_spec = obj._registry.specs[dep_inst]
                assert(spec2.name < dep_inst)
                assert(spec.test_key == dep_inst_spec.inj_key)
            case x:
                assert(False), x


    def test_build_dep_match_with_injection_fail(self, network):
        obj = network
        relation = {"task":"basic::dep", "inject":{"from_spec":{"inj_key":"{bad_key}"}}}
        spec  = TaskSpec.build({"name":"basic::task",
                                "depends_on":[relation],
                                "test_key": "bloo"})
        spec2 = TaskSpec.build({"name":"basic::dep"})
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        assert(not bool(obj._registry.concrete[spec2.name]))
        with pytest.raises(doot.errors.TrackingError):
            obj.build_network()

    def test_build_dep_chain_transitive_injection(self, network):
        """
          check a inject can be chained.
          test_key=bloo should be carried from basic::task to basic::dep to basic::chained
        """
        obj = network
        spec  = TaskSpec.build({"name":"basic::task", "depends_on":[{"task":"basic::dep", "inject":{"from_spec":["test_key"]}}], "test_key": "bloo"})
        spec2 = TaskSpec.build({"name":"basic::dep",  "depends_on": [{"task":"basic::chained", "inject":{"from_spec":["test_key"]}}], "test_key": "blah"})
        spec3 = TaskSpec.build({"name":"basic::chained", "test_key": "aweg"})
        obj._registry.register_spec(spec, spec2, spec3)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 7)
        match list(obj.pred[instance]):
            case [TaskName() as dep_inst]:
                assert(spec2.name < dep_inst)
                assert(spec.test_key == obj._registry.specs[dep_inst].test_key)
                dep_spec = obj._registry.specs[dep_inst]
                assert(spec2.name <= dep_spec.sources[-1])
                assert(dep_spec.test_key != spec2.test_key)
            case x:
                assert(False), x

        match list(obj.pred[dep_inst]):
            case [TaskName() as chain_inst]:
                assert(spec3.name < chain_inst)
                assert(spec.test_key == obj._registry.specs[chain_inst].test_key)
                chain_spec = obj._registry.specs[chain_inst]
                assert(spec3.name < chain_spec.sources[-1])
                assert(chain_spec.test_key != spec3.test_key)
            case x:
                assert(False), x

    def test_build_req_chain_with_transitive_injections(self, network):
        """ Construct a requirement, rather than dependency, chain,
          passing the injection up the chain
          """
        obj = network
        # Abstract specs
        spec  = TaskSpec.build({"name":"basic::task",
                                             "required_for":[{"task":"basic::req", "inject":{"from_spec": ["test_key"]}}],
                                             "test_key": "bloo"})
        spec2 = TaskSpec.build({"name":"basic::req",
                                             "required_for": [{"task":"basic::chained", "inject":{"from_spec": ["test_key"]}}],
                                             "must_inject":["test_key"],
                                             })
        spec3 = TaskSpec.build({"name":"basic::chained", "must_inject":["test_key"]})
        obj._registry.register_spec(spec, spec2, spec3)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 7)
        match list(obj.succ[instance]):
            case [_, TaskName() as req_inst, TaskName() as cleanup_inst]:
                assert(spec2.name < req_inst)
                assert(spec.name < cleanup_inst)
                assert(cleanup_inst.is_cleanup())
                # Test concrete specs have carried the injection:
                assert(obj._registry.specs[req_inst].test_key == spec.test_key)
            case x:
                assert(False), x

        match list(obj.succ[req_inst]):
            case [TaskName() as chain_inst, TaskName() as req_cleanup]:
                assert(spec3.name < chain_inst)
                assert(spec2.name < req_cleanup)
                assert(req_cleanup.is_cleanup())
                assert(obj._registry.specs[chain_inst].test_key == spec.test_key)
            case x:
                assert(False), x

class TestTrackerNetworkBuild_Jobs:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_build_job(self, network):
        """ a job should build a ..$head$ as well,
        and the head should build a ..$cleanup$ """
        obj         = network
        spec        = TaskSpec.build({"name":"basic::+.job", "meta": ["JOB"]})
        job_head    = spec.name.with_head()
        job_cleanup = job_head.with_cleanup()
        obj._registry.register_spec(spec)
        assert(len(obj) == 1) # Root node
        assert(len(obj._registry.specs) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        instance = obj._registry._instantiate_spec(spec.name)
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(len(obj) == 4)
        assert(instance in obj)
        match obj._registry.concrete.get(job_head, None):
            case [TaskName() as head_instance]:
                assert(head_instance in obj.succ[instance])
                pass
            case x:
                assert(False), x

        match obj._registry.concrete.get(job_cleanup, None):
            case [TaskName() as cleanup_instance]:
                assert(cleanup_instance in obj.succ[head_instance])
            case x:
                assert(False), x

    def test_build_with_head_dep(self, network):
        obj = network
        spec  = TaskSpec.build({"name":"basic::task",
                                "depends_on":["basic::+.job..$head$"]})
        spec2 = TaskSpec.build({"name":"basic::+.job"})
        assert(TaskMeta_e.JOB in spec2.name)
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        assert(spec.name in obj._registry.concrete)
        assert(spec2.name.with_head() in obj._registry.concrete)
        assert(spec2.name in obj._registry.concrete)
        obj.validate_network()

class TestTrackerNetworkBuild_Artifacts:

    def test_sanity(self):
        assert(True is not False) # noqa: PLR0133

    def test_build_dep_chain_with_artifact(self, network):
        """check basic::task triggers basic::dep via the intermediary of the artifact test.blah"""
        obj   = network
        spec  = TaskSpec.build({"name":"basic::task", "depends_on":["file::>test.blah"]})
        spec2 = TaskSpec.build({"name":"basic::dep", "required_for":["file::>test.blah"]})
        obj._registry.register_spec(spec, spec2)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(not bool(obj.adj[obj._root_node]))
        obj.connect(instance)
        assert(len(obj) == 2)
        obj.build_network()
        obj.validate_network()
        assert(len(obj) == 6)
        # Check theres a path between the specs, via the artifact
        match obj._registry.concrete.get(spec2.name, None):
            case [TaskName() as dep_inst]:
                assert(spec2.name < dep_inst)
                assert(nx.has_path(obj._graph, dep_inst, instance))
            case x:
                assert(False), x

    def test_build_with_concrete_artifact(self, network):
        obj = network
        spec  = TaskSpec.build({"name":"basic::task", "depends_on":["file::>basic.txt"]})
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
        spec  = TaskSpec.build({"name":"basic::task", "required_for":["file::>basic.txt"]})
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
        spec  = TaskSpec.build({"name":"basic::task", "depends_on":["file::>*.txt"]})
        obj._registry.register_spec(spec)
        instance = obj._registry._instantiate_spec(spec.name)
        assert(len(obj) == 1)
        assert(len(obj._registry.artifacts) == 1)
        obj.connect(instance)
        obj.build_network()
        assert(spec.depends_on[0].target in obj.pred[instance])

    @pytest.mark.xfail
    def test_build_abstract_artifact_chain(self, network):
        obj = network
        consumer     = TaskSpec.build({"name":"basic::consumer", "depends_on":["file::>*.txt"]})
        producer     = TaskSpec.build({"name":"basic::producer", "required_for":["file::>blah.txt"]})
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
