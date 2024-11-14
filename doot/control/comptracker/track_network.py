#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
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

from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload, NewType,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import networkx as nx
import tomlguard
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import Job_i, Task_i, TaskRunner_i, TaskTracker_i
from doot._structs.relation_spec import RelationSpec
from doot.enums import TaskMeta_f, QueueMeta_e, TaskStatus_e, LocationMeta_f, RelationMeta_e, EdgeType_e
from doot.structs import (ActionSpec, TaskArtifact,
                          TaskName, TaskSpec)
from doot.task.base_task import DootTask
from doot.utils.injection import Injector_m
from doot.utils.matching import TaskMatcher_m
# ##-- end 1st party imports

##-- logging
logging          = logmod.getLogger(__name__)
printer          = doot.subprinter()
track_l          = doot.subprinter("track")
logging.disabled = False
##-- end logging

ROOT                            : Final[str]                  = "root::_" # Root node of dependency graph
EXPANDED                        : Final[str]                  = "expanded"  # Node attribute name
REACTIVE_ADD                    : Final[str]                  = "reactive-add"
CLEANUP                         : Final[str]                  = "cleanup"
ARTIFACT_EDGES                  : Final[set[EdgeType_e]]      = EdgeType_e.artifact_edge_set
DECLARE_PRIORITY                : Final[int]                  = 10
MIN_PRIORITY                    : Final[int]                  = -10
INITIAL_SOURCE_CHAIN_COUNT      : Final[int]                  = 10

T                                                              = TypeVar("T")
Abstract                                                       = NewType("Abstract", T)
Concrete                                                       = NewType("Concrete", T)

ActionElem                      : TypeAlias                   = ActionSpec|RelationSpec
ActionGroup                     : TypeAlias                   = list[ActionElem]

class TrackNetwork(TaskMatcher_m):
    """ The _graph of concrete tasks and their dependencies """

    def __init__(self, registry:TrackRegistry):
        self._registry                                                       = registry
        self._root_node        : TaskName                                    = TaskName.build(ROOT)
        self._declare_priority : int                                         = DECLARE_PRIORITY
        self._min_priority     : int                                         = MIN_PRIORITY
        self._graph            : nx.DiGraph[Concrete[TaskName]|TaskArtifact] = nx.DiGraph()
        self.is_valid          : bool                                        = False

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

    def _add_node(self, name:Concrete[TaskName]|TaskArtifact) -> None:
        """idempotent"""
        match name:
            case x if x is self._root_node:
                self._graph.add_node(name)
                self.nodes[name][EXPANDED]     = True
                self.nodes[name][REACTIVE_ADD] = False
                self._root_node.meta                  |= TaskMeta_f.CONCRETE
            case TaskName() if TaskMeta_f.CONCRETE not in name:
                raise doot.errors.DootTaskTrackingError("Nodes should only be instantiated spec names", name)
            case _ if name in self.nodes:
                return
            case TaskArtifact():
                # Add node with metadata
                logging.debug("Inserting Artifact into _graph: %s", name)
                self._graph.add_node(name)
                self.nodes[name][EXPANDED]     = False
                self.nodes[name][REACTIVE_ADD] = False
                self.is_valid = False
            case TaskName():
                # Add node with metadata
                logging.debug("Inserting ConcreteId into _graph: %s", name)
                self._graph.add_node(name)
                self.nodes[name][EXPANDED]     = False
                self.nodes[name][REACTIVE_ADD] = False
                self.is_valid = False

    def _match_artifact_to_transformers(self, artifact:TaskArtifact) -> set[Concrete[TaskName]]:
        """
          Match and instantiate artifact transformers when applicable
          filters out transformers which are already connected to the artifact.
        """
        logging.debug("-- Instantiating Artifact Relevant Transformers")
        assert(artifact in self.nodes)
        to_expand              = set()
        available_transformers = set()
        local_nodes            = set()
        local_nodes.update(self.pred[artifact].keys())
        local_nodes.update(self.succ[artifact].keys())

        # ignore unrelated artifacts

        def abstraction_test(x:TaskArtifact) -> bool:
            return artifact in x and x in self._registry._transformer_specs

        for abstract in [x for x in self._registry._abstract_artifacts if abstraction_test(x)]:
            # And get transformers of related _registry.artifacts
            available_transformers.update(self._registry._transformer_specs[abstract])

        filtered = (available_transformers - local_nodes)
        logging.debug("Transformers: %s available, %s local nodes, %s when filtered", len(available_transformers), len(local_nodes), len(filtered))
        for transformer in filtered:
            if bool(local_nodes.intersection(self._registry.concrete[transformer])):
                continue
            match self._registry._instantiate_transformer(transformer, artifact):
                case None:
                    pass
                case TaskName() as instance:
                    logging.debug("-- Matching Transformer found: %s", transformer)
                    spec = self._registry.specs[instance]
                    # A transformer *always* has at least 1 dependency and requirement,
                    # which is *always* the updated artifact relations
                    if spec.depends_on[-1].target == artifact:
                        self.connect(artifact, instance)
                    elif spec.required_for[-1].target == artifact:
                        self.connect(instance, artifact)
                    else:
                        raise doot.errors.DootTaskTrackingError("instantiated a transformer that doesn't match the artifact which triggered it", artifact, spec)

                    to_expand.add(instance)

        return to_expand

    def _expand_task_node(self, name:Concrete[TaskName]) -> set[Concrete[TaskName]|TaskArtifact]:
        """ expand a task node, instantiating and connecting to its dependencies and dependents,
        *without* expanding those new nodes.
        returns a list of the new nodes tasknames
        """
        assert(name.is_instantiated())
        assert(not self.nodes[name].get(EXPANDED, False))
        spec                                                  = self._registry.specs[name]
        spec_pred, spec_succ                                  = self.pred[name], self.succ[name]
        to_expand                                             = set()

        track_l.debug("--> Expanding Task: %s : Pre(%s), Post(%s)", name, len(spec.depends_on), len(spec.required_for))
        logging.debug("--> Expanding Task: %s : Pre(%s), Post(%s)", name, len(spec.depends_on), len(spec.required_for))

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
            self.nodes[name][EXPANDED] = True

        to_expand.update(self._generate_node_subtasks(spec))
        to_expand.update(self._generate_successor_edges(spec))
        track_l.debug("<-- Task Expansion Complete: %s", name)
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
        blockers  = self._registry._blockers[spec.name.root(top=True)]

        # Try to link instantiated nodes if they match constraints

        # else instantiate and link new nodes

        return to_expand

    def _generate_node_subtasks(self, spec:Concrete[TaskSpec]) -> list[Concrete[TaskName]]:
        """
          instantiate and connect a job's head task
          TODO these could be shifted into the task/job class
        """

        if TaskMeta_f.JOB in spec.name:
            logging.debug("Expanding Job Head for: %s", spec.name)
            heads         = [jhead for x in spec.get_source_names() if (jhead:=x.job_head()) in self._registry.specs]
            head_name     = heads[-1]
            head_instance = self._registry._instantiate_spec(head_name, extra=spec.model_extra)
            self.connect(spec.name, head_instance, job_head=True)
            return [head_instance]

        if spec.name.is_instantiated() and (root:=spec.name.root()) == root.cleanup_name():
            return []

        # Instantiate and connect the cleanup task
        cleanup = self._registry._instantiate_spec(spec.name.cleanup_name())
        self.connect(spec.name, cleanup, cleanup=True)
        return [cleanup]

    def _expand_artifact(self, artifact:TaskArtifact) -> set[Concrete[TaskName]|TaskArtifact]:
        """ expand _registry.artifacts, instantiating related tasks/transformers,
          and connecting the task to its abstract/concrete related _registry.artifacts
          """
        assert(artifact in self._registry.artifacts)
        assert(artifact in self.nodes)
        assert(not self.nodes[artifact].get(EXPANDED, False))
        logging.debug("--> Expanding Artifact: %s", artifact)
        to_expand = set()

        logging.debug("-- Instantiating Artifact relevant tasks")
        for name in list(self._registry.artifacts[artifact]):
            instance = self._registry._instantiate_spec(name)
            # Don't connect it to the _graph, it'll be expanded later
            self.connect(instance, False)
            to_expand.add(instance)

        to_expand.update(self._match_artifact_to_transformers(artifact))

        match artifact.is_concrete():
            case True:
                logging.debug("-- Connecting concrete artifact to parent abstracts")
                for abstract in [x for x in self._registry._abstract_artifacts if artifact in x and LocationMeta_f.glob in x]:
                    self.connect(artifact, abstract)
                    to_expand.add(abstract)
            case False:
                logging.debug("-- Connecting abstract task to child concrete _registry.artifacts")
                for conc in [x for x in self._registry._concrete_artifacts if x in artifact]:
                    assert(conc in artifact)
                    self.connect(conc, artifact)
                    to_expand.add(conc)

        logging.debug("<-- Artifact Expansion Complete: %s", artifact)
        self.nodes[artifact][EXPANDED] = True
        return to_expand

    def concrete_edges(self, name:Concrete[TaskName|TaskArtifact]) -> tomlguard.TomlGuard:
        """ get the concrete edges of a task.
          ie: the ones in the task _graph, not the abstract ones in the spec.
        """
        assert(name in self)
        preds = self.pred[name]
        succ  = self.succ[name]
        return tomlguard.TomlGuard({
            "pred" : {"tasks": [x for x in preds if isinstance(x, TaskName)],
                      "_registry.artifacts": {"abstract": [x for x in preds if isinstance(x, TaskArtifact) and not x.is_concrete()],
                                    "concrete": [x for x in preds if isinstance(x, TaskArtifact) and x.is_concrete()]}},
            "succ" : {"tasks": [x for x in succ  if isinstance(x, TaskName) and x is not self._root_node],
                      "_registry.artifacts": {"abstract": [x for x in succ if isinstance(x, TaskArtifact) and not x.is_concrete()],
                                    "concrete": [x for x in succ if isinstance(x, TaskArtifact) and x.is_concrete()]}},
            "root" : self._root_node in succ,
            })

    def connect(self, left:None|Concrete[TaskName]|TaskArtifact, right:None|False|Concrete[TaskName]|TaskArtifact=None, **kwargs) -> None:
        """
        Connect a task node to another. left -> right
        If given left, None, connect left -> ROOT
        if given left, False, just add the node

        (This preserves graph.pred[x] as the nodes x is dependent on)
        """
        assert("type" not in kwargs)
        self.is_valid = False
        match left:
            case x if x == self._root_node:
                pass
            case TaskName() if left not in self._registry.specs:
                raise doot.errors.DootTaskTrackingError("Can't connect a non-existent task", left)
            case TaskArtifact() if left not in self._registry.artifacts:
                raise doot.errors.DootTaskTrackingError("Can't connect a non-existent artifact", left)
            case _ if left not in self.nodes:
                self._add_node(left)

        match right:
            case False:
                return
            case None:
                right = self._root_node
            case TaskName() if right not in self._registry.specs:
                raise doot.errors.DootTaskTrackingError("Can't connect a non-existent task", right)
            case TaskArtifact() if right not in self._registry.artifacts:
                raise doot.errors.DootTaskTrackingError("Can't connect a non-existent artifact", right)
            case _ if right not in self.nodes:
                self._add_node(right)

        if right in self.succ[left]:
            # nothing to do
            return

        logging.debug("Connecting: %s -> %s", left, right)
        # Add the edge, with metadata
        match left, right:
            case TaskName(), TaskName():
                self._graph.add_edge(left, right, type=EdgeType_e.TASK, **kwargs)
            case TaskName(), TaskArtifact():
                self._graph.add_edge(left, right, type=EdgeType_e.TASK_CROSS, **kwargs)
            case TaskArtifact(), TaskName():
                self._graph.add_edge(left, right, type=EdgeType_e.ARTIFACT_CROSS, **kwargs)
            case TaskArtifact(), TaskArtifact() if left.is_concrete() and right.is_concrete():
                raise doot.errors.DootTaskTrackingError("Tried to connect two concrete _registry.artifacts", left, right)
            case TaskArtifact(), TaskArtifact() if right.is_concrete():
                self._graph.add_edge(left, right, type=EdgeType_e.ARTIFACT_UP, **kwargs)
            case TaskArtifact(), TaskArtifact() if not right.is_concrete():
                self._graph.add_edge(left, right, type=EdgeType_e.ARTIFACT_DOWN, **kwargs)

    def validate_network(self, *, strict:bool=True) -> bool:
        """ Finalise and ensure consistence of the task _graph.
        run tests to check the dependency graph is acceptable
        """
        logging.debug("Validating Task Network")
        if not nx.is_directed_acyclic_graph(self._graph):
            raise doot.errors.DootTaskTrackingError("Network isn't a DAG")

        for node, data in self.nodes.items():
            match node:
                case TaskName() | TaskArtifact() if not data[EXPANDED]:
                    if strict:
                        raise doot.errors.DootTaskTrackingError("Network isn't fully expanded", node)
                    else:
                        logging.warning("Network isn't fully expanded: %s", node)
                case TaskName() if TaskMeta_f.CONCRETE not in node:
                    if strict:
                        raise doot.errors.DootTaskTrackingError("Abstract ConcreteId in _graph", node)
                    else:
                        logging.warning("Abstract ConcreteId in _graph: %s", node)
                case TaskArtifact() if LocationMeta_f.glob in node:
                    bad_nodes = [x for x in self.pred[node] if x in self._registry.specs]
                    if strict and bool(bad_nodes):
                        raise doot.errors.DootTaskTrackingError("Glob Artifact ConcreteId is a successor to a task", node, bad_nodes)
                    elif bool(bad_nodes):
                        logging.warning("Glob Artifact ConcreteId is a successor to a task: %s (%s)", node, bad_nodes)

    def incomplete_dependencies(self, focus:Concrete[TaskName]|TaskArtifact) -> list[Concrete[TaskName]|TaskArtifact]:
        """ Get all predecessors of a node that don't evaluate as complete """
        assert(focus in self.nodes)
        incomplete = []
        for x in [x for x in self.pred[focus] if self._registry.get_status(x) not in TaskStatus_e.success_set]:
            match x:
                case TaskName() if CLEANUP in self.edges[x, focus]:
                    pass
                case TaskName() if x not in self._registry.tasks:
                    incomplete.append(x)
                case TaskName() if not bool(self._registry.tasks[x]):
                    incomplete.append(x)
                case TaskArtifact() if not bool(x):
                    incomplete.append(x)

        return incomplete

    def build_network(self, *, sources:None|True|list[Concrete[TaskName]|TaskArtifact]=None) -> None:
        """
        for each task queued (ie: connected to the root node)
        expand its dependencies and add into the _graph, until no mode nodes to expand.
        then connect concrete _registry.artifacts to abstract _registry.artifacts.

        # TODO _graph could be built in total, or on demand
        """
        logging.debug("-> Building Task Network")
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
            logging.debug("- Processing: %s", queue[-1])
            match (current:=queue.pop()):
                case x if x in processed or self.nodes[x].get(EXPANDED, False):
                    logging.debug("- Processed already")
                    processed.add(x)
                case TaskName() as x if x in self.nodes:
                    additions = self._expand_task_node(x)
                    logging.debug("- Task Expansion produced: %s", additions)
                    queue    += additions
                    processed.add(x)
                case TaskArtifact() as x if x in self.nodes:
                    additions = self._expand_artifact(x)
                    logging.debug("- Artifact Expansion produced: %s", additions)
                    queue += additions
                    processed.add(x)
                case _:
                    raise doot.errors.DootTaskTrackingError("Unknown value in _graph")

        else:
            logging.debug("- Final Network Nodes: %s", self.nodes)
            logging.debug("<- Final Network Edges: %s", self.edges)
            self.is_valid = True
            pass
