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
import re
import time
import types
import weakref
from collections import defaultdict
from itertools import chain, cycle
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto, Mixin
import networkx as nx
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.dkey import DKey
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._structs.relation_spec import RelationSpec
from doot.enums import TaskStatus_e, EdgeType_e, ArtifactStatus_e
from doot.structs import (ActionSpec, TaskArtifact, TaskName, TaskSpec)
from doot.task.core.task import DootTask
from doot.mixins.matching import TaskMatcher_m
# ##-- end 1st party imports

from . import _interface as API # noqa: N812

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
    from .track_registry import TrackRegistry
    type Abstract[T] = T
    type Concrete[T] = T

    type ActionElem  = ActionSpec|RelationSpec
    type ActionGroup = list[ActionElem]
##--|

# isort: on
# ##-- end types

##-- logging
logging          = logmod.getLogger(__name__)
logging.disabled = False
##-- end logging

##--|

class _Expansion_m:

    def build_network(self, *, sources:Maybe[True|list[Concrete[TaskName]|TaskArtifact]]=None) -> None:
        """
        for each task queued (ie: connected to the root node)
        expand its dependencies and add into the _graph, until no mode nodes to expand.
        then connect concrete _registry.artifacts to abstract _registry.artifacts.

        # TODO _graph could be built in total, or on demand
        """
        logging.trace("-> Building Task Network")
        match sources:
            case None:
                queue = list(self.pred[self._root_node].keys())
            case True:
                queue = list(self.nodes.keys())
            case [*xs]:
                queue = list(sources)
        processed = { self._root_node }
        logging.info("Initial Network Queue: %s", queue)
        while bool(queue): # expand tasks
            logging.detail("- Processing: %s", queue[-1])
            match (current:=queue.pop()):
                case x if x in processed or self.nodes[x].get(API.EXPANDED, False):
                    logging.detail("- Processed already")
                    processed.add(x)
                case TaskName() as x if x in self.nodes:
                    additions = self._expand_task_node(x)
                    logging.detail("- Task Expansion produced: %s", additions)
                    queue    += additions
                    processed.add(x)
                case TaskArtifact() as x if x in self.nodes:
                    additions = self._expand_artifact(x)
                    logging.detail("- Artifact Expansion produced: %s", additions)
                    queue += additions
                    processed.add(x)
                case _:
                    raise doot.errors.TrackingError("Unknown value in _graph")

        else:
            logging.detail("- Final Network Nodes: %s", self.nodes)
            logging.trace("<- Final Network Edges: %s", self.edges)
            self.is_valid = True
            pass

    def connect(self, left:Maybe[Concrete[TaskName]|TaskArtifact], right:Maybe[False|Concrete[TaskName]|TaskArtifact]=None, **kwargs) -> None:
        """
        Connect a task node to another. left -> right
        If given left, None, connect left -> API.ROOT
        if given left, False, just add the node

        (This preserves graph.pred[x] as the nodes x is dependent on)
        """
        assert("type" not in kwargs)
        self.is_valid = False
        match left:
            case x if x == self._root_node:
                pass
            case TaskName() if left not in self._registry.specs:
                raise doot.errors.TrackingError("Can't connect a non-existent task", left)
            case TaskArtifact() if left not in self._registry.artifacts:
                raise doot.errors.TrackingError("Can't connect a non-existent artifact", left)
            case _ if left not in self.nodes:
                self._add_node(left)

        match right:
            case False:
                return
            case None:
                right = self._root_node
            case TaskName() if right not in self._registry.specs:
                raise doot.errors.TrackingError("Can't connect a non-existent task", right)
            case TaskArtifact() if right not in self._registry.artifacts:
                raise doot.errors.TrackingError("Can't connect a non-existent artifact", right)
            case _ if right not in self.nodes:
                self._add_node(right)

        if right in self.succ[left]:
            # nothing to do
            return

        logging.detail("Connecting: %s -> %s", left, right)
        # Add the edge, with metadata
        match left, right:
            case TaskName(), TaskName():
                self._graph.add_edge(left, right, type=EdgeType_e.TASK, **kwargs)
            case TaskName(), TaskArtifact():
                self._graph.add_edge(left, right, type=EdgeType_e.TASK_CROSS, **kwargs)
            case TaskArtifact(), TaskName():
                self._graph.add_edge(left, right, type=EdgeType_e.ARTIFACT_CROSS, **kwargs)
            case TaskArtifact(), TaskArtifact() if left.is_concrete() and right.is_concrete():
                raise doot.errors.TrackingError("Tried to connect two concrete _registry.artifacts", left, right)
            case TaskArtifact(), TaskArtifact() if right.is_concrete():
                self._graph.add_edge(left, right, type=EdgeType_e.ARTIFACT_UP, **kwargs)
            case TaskArtifact(), TaskArtifact() if not right.is_concrete():
                self._graph.add_edge(left, right, type=EdgeType_e.ARTIFACT_DOWN, **kwargs)

    def _add_node(self, name:Concrete[TaskName]|TaskArtifact) -> None:
        """idempotent"""
        match name:
            case x if x is self._root_node:
                self._graph.add_node(name)
                self.nodes[name][API.EXPANDED]     = True
                self.nodes[name][API.REACTIVE_ADD] = False
            case TaskName() if TaskName.bmark_e.gen not in name:
                raise doot.errors.TrackingError("Nodes should only be instantiated spec names", name)
            case _ if name in self.nodes:
                return
            case TaskArtifact():
                # Add node with metadata
                logging.trace("Inserting Artifact into graph: %s", name)
                self._graph.add_node(name)
                self.nodes[name][API.EXPANDED]     = False
                self.nodes[name][API.REACTIVE_ADD] = False
                self.is_valid = False
            case TaskName():
                # Add node with metadata
                logging.trace("Inserting Task into graph: %s", name)
                self._graph.add_node(name)
                self.nodes[name][API.EXPANDED]     = False
                self.nodes[name][API.REACTIVE_ADD] = False
                self.is_valid = False

    def _expand_task_node(self, name:Concrete[TaskName]) -> set[Concrete[TaskName]|TaskArtifact]:
        """ expand a task node, instantiating and connecting to its dependencies and dependents,
        *without* expanding those new nodes.
        returns a list of the new nodes tasknames
        """
        assert(name.is_uniq())
        assert(not self.nodes[name].get(API.EXPANDED, False))
        spec                                                  = self._registry.specs[name]
        spec_pred, spec_succ                                  = self.pred[name], self.succ[name]
        to_expand                                             = set()

        logging.trace("--> Expanding Task: %s : Pre(%s), Post(%s)", name, len(spec.depends_on), len(spec.required_for))

        # Connect Relations
        for rel in itz.chain(spec.action_group_elements()):
            if not isinstance(rel, RelationSpec):
                # Ignore Actions
                continue
            relevant_edges = spec_succ if rel.forward_dir_p() else spec_pred
            match rel:
                case RelationSpec(target=TaskArtifact() as target):
                    # Connect the artifact mentioned
                    assert(target in self._registry.artifacts)
                    self.connect(*rel.to_ordered_pair(name))
                    to_expand.add(target)
                case RelationSpec(target=TaskName()) if self.match_edge(rel, relevant_edges.keys(), exclude=[name]):
                    # already linked, ignore.
                    continue
                case RelationSpec(target=TaskName()):
                    # Get specs and instances with matching target
                    instance = self._registry._instantiate_relation(rel, control=name)
                    self.connect(*rel.to_ordered_pair(name, target=instance))
                    to_expand.add(instance)
        else:
            assert(name in self.nodes)
            self.nodes[name][API.EXPANDED] = True

        to_expand.update(self._generate_node_subtasks(spec))
        to_expand.update(self._generate_successor_edges(spec))
        logging.detail("<-- Task Expansion Complete: %s", name)
        return to_expand

    def _generate_successor_edges(self, spec:Concrete[TaskSpec]) -> set[Concrete[TaskName]|TaskArtifact]:
        """ for a spec S, find the tasks T that have registered a relation
        of T < S.
        (S would not know about these blockers).

        For these T, link instantiated nodes that match constraints and link them to S,
        or if no nodes exist, create and link them.
        """
        to_expand = set()
        spec_pred = self.pred[spec.name]
        # Get (abstract) blocking relations from self._blockers
        blockers  = self._registry._blockers[spec.name.pop(top=True)]

        # Try to link instantiated nodes if they match constraints

        # else instantiate and link new nodes

        return to_expand

    def _generate_node_subtasks(self, spec:Concrete[TaskSpec]) -> list[Concrete[TaskName]]:
        """
          instantiate and connect a job's head task
          TODO these could be shifted into the task/job class
        """

        if TaskSpec.mark_e.JOB in spec.meta:
            logging.trace("Generating Job Head for: %s", spec.name)
            head_name     = spec.name.de_uniq().with_head()
            head_instance = self._registry._instantiate_spec(head_name, extra=spec.model_extra)
            self.connect(spec.name, head_instance, job_head=True)
            return [head_instance]

        if not spec.name.is_cleanup():
            # Instantiate and connect the cleanup task
            cleanup_name = spec.name.de_uniq().with_cleanup()
            cleanup = self._registry._instantiate_spec(cleanup_name)
            self.connect(spec.name, cleanup, cleanup=True)
            return [cleanup]

        return []

    def _expand_artifact(self, artifact:TaskArtifact) -> set[Concrete[TaskName]|TaskArtifact]:
        """ expand _registry.artifacts, instantiating related tasks,
          and connecting the task to its abstract/concrete related _registry.artifacts
          """
        assert(artifact in self._registry.artifacts)
        assert(artifact in self.nodes)
        assert(not self.nodes[artifact].get(API.EXPANDED, False))
        logging.trace("--> Expanding Artifact: %s", artifact)
        to_expand = set()

        logging.detail("-- Instantiating Artifact relevant tasks")
        for name in list(self._registry.artifacts[artifact]):
            instance = self._registry._instantiate_spec(name)
            # Don't connect it to the _graph, it'll be expanded later
            self.connect(instance, False)
            to_expand.add(instance)

        match artifact.is_concrete():
            case True:
                logging.detail("-- Connecting concrete artifact to parent abstracts")
                art_path = DKey(artifact[1:], mark=DKey.Mark.PATH)(relative=True)
                for abstract in self._registry._abstract_artifacts:
                    if art_path not in abstract and artifact not in abstract:
                        continue
                    self.connect(artifact, abstract)
                    to_expand.add(abstract)
            case False:
                logging.detail("-- Connecting abstract task to child concrete _registry.artifacts")
                for conc in self._registry._concrete_artifacts:
                    assert(conc.is_concrete())
                    conc_path = DKey(conc[1:], mark=DKey.Mark.PATH)(relative=True)
                    if conc_path not in artifact:
                        continue
                    self.connect(conc, artifact)
                    to_expand.add(conc)

        logging.trace("<-- Artifact Expansion Complete: %s", artifact)
        self.nodes[artifact][API.EXPANDED] = True
        return to_expand

class _Validation_m:

    def validate_network(self, *, strict:bool=True) -> bool:
        """ Finalise and ensure consistence of the task _graph.
        run tests to check the dependency graph is acceptable
        """
        logging.trace("Validating Task Network")
        if not nx.is_directed_acyclic_graph(self._graph):
            raise doot.errors.TrackingError("Network isn't a DAG")

        for node, data in self.nodes.items():
            match node:
                case TaskName() as x if x == self._root_node:
                    pass
                case TaskName() | TaskArtifact() if not data[API.EXPANDED]:
                    if strict:
                        raise doot.errors.TrackingError("Network isn't fully expanded", node)
                    else:
                        logging.user("Network isn't fully expanded: %s", node)
                case TaskName() if not node.is_uniq():
                    if strict:
                        raise doot.errors.TrackingError("Abstract ConcreteId in _graph", node)
                    else:
                        logging.user("Abstract ConcreteId in graph: %s", node)
                case TaskArtifact() if TaskArtifact.bmark_e.glob in node:
                    # If a node is abtract, it needs to be attacked to something
                    no_ctor = not bool(self.network.pred[node])
                    msg = "Abtract Artifact has not predecessors"
                    if strict and no_ctor:
                        raise doot.errors.TrackingError(msg, node)
                    elif no_ctor:
                        logging.user(msg, node)

    def concrete_edges(self, name:Concrete[TaskName|TaskArtifact]) -> ChainGuard:
        """ get the concrete edges of a task.
          ie: the ones in the task _graph, not the abstract ones in the spec.
        """
        assert(name in self)
        preds = self.pred[name]
        succ  = self.succ[name]
        return ChainGuard({
            "pred" : {"tasks": [x for x in preds if isinstance(x, TaskName)],
                      "_registry.artifacts": {"abstract": [x for x in preds if isinstance(x, TaskArtifact) and not x.is_concrete()],
                                    "concrete": [x for x in preds if isinstance(x, TaskArtifact) and x.is_concrete()]}},
            "succ" : {"tasks": [x for x in succ  if isinstance(x, TaskName) and x is not self._root_node],
                      "_registry.artifacts": {"abstract": [x for x in succ if isinstance(x, TaskArtifact) and not x.is_concrete()],
                                    "concrete": [x for x in succ if isinstance(x, TaskArtifact) and x.is_concrete()]}},
            "root" : self._root_node in succ,
            })

    def incomplete_dependencies(self, focus:Concrete[TaskName]|TaskArtifact) -> list[Concrete[TaskName]|TaskArtifact]:
        """ Get all predecessors of a node that don't evaluate as complete """
        assert(focus in self.nodes)
        incomplete = []
        for x in self.pred[focus]:
            status = self._registry.get_status(x)
            is_success = status in TaskStatus_e.success_set or status is ArtifactStatus_e.EXISTS
            match x:
                case _ if is_success:
                    pass
                case TaskName() if API.CLEANUP in self.edges[x, focus]:
                    pass
                case TaskName() if x not in self._registry.tasks:
                    incomplete.append(x)
                case TaskName() if not bool(self._registry.tasks[x]):
                    incomplete.append(x)
                case TaskArtifact() if not bool(x):
                    incomplete.append(x)
        else:
            return incomplete

##--|

@Mixin(_Expansion_m, _Validation_m, TaskMatcher_m)
class TrackNetwork:
    """ The _graph of concrete tasks and their dependencies """
    _registry         : TrackRegistry
    _root_node        : TaskName
    _declare_priority : int
    _min_priority     : int
    _graph            : nx.DiGraph[Concrete[TaskName]|TaskArtifact]
    is_valid          : bool

    def __init__(self, registry:TrackRegistry):
        self._registry         = registry
        self._root_node        = TaskName(API.ROOT)
        self._declare_priority = API.DECLARE_PRIORITY
        self._min_priority     = API.MIN_PRIORITY
        self._graph            = nx.DiGraph()
        self.is_valid          = False

        self._add_node(self._root_node)

    @property
    def nodes(self):
        return self._graph.nodes

    @property
    def edges(self):
        return self._graph.edges

    @property
    def pred(self):
        return self._graph.pred

    @property
    def adj(self):
        return self._graph.adj

    @property
    def succ(self):
        return self._graph.succ

    def __len__(self):
        return len(self._graph)

    def __contains__(self, other:Concrete[TaskName]|TaskArtifact):
        return other in self._graph
