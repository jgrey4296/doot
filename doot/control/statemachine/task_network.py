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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
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
from doot._abstract import (FailPolicy_p, Job_i, Task_i, TaskRunner_i,
                            TaskTracker_i)
from doot._structs.relation_spec import RelationSpec
from doot.enums import (EdgeType_e, LocationMeta_f, QueueMeta_e,
                        RelationMeta_e, TaskMeta_f, TaskStatus_e)
from doot.structs import (ActionSpec, CodeReference, TaskArtifact, TaskName,
                          TaskSpec)
from doot.task.base_task import DootTask

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

ROOT                           : Final[str]                  = "root::_" # Root node of dependency graph
EXPANDED                       : Final[str]                  = "expanded"  # Node attribute name
REACTIVE_ADD                   : Final[str]                  = "reactive-add"
ARTIFACT_EDGES                 : Final[set[EdgeType_e]]      = EdgeType_e.artifact_edge_set
DECLARE_PRIORITY               : Final[int]                  = 10
MIN_PRIORITY                   : Final[int]                  = -10
INITIAL_SOURCE_CHAIN_COUNT      : Final[int]                  = 10

AbstractId                     : TypeAlias                   = TaskName|TaskArtifact
ConcreteId                     : TypeAlias                   = TaskName|TaskArtifact
AnyId                          : TypeAlias                   = TaskName|TaskArtifact
AbstractSpec                   : TypeAlias                   = TaskSpec
ConcreteSpec                   : TypeAlias                   = TaskSpec
AnySpec                        : TypeAlias                   = TaskSpec

ActionElem                     : TypeAlias                   = ActionSpec|RelationSpec
ActionGroup                    : TypeAlias                   = list[ActionElem]


class TaskNetwork:
    """ The network of concrete tasks and their dependencies """

    def __init__(self, registry:TaskRegistry):
        self._registry                                                     = registry
        self._root_node        : TaskName                                  = TaskName.build(ROOT)
        self._declare_priority : int                                       = DECLARE_PRIORITY
        self._min_priority     : int                                       = MIN_PRIORITY
        self.network           : nx.DiGraph[ConcreteId]                    = nx.DiGraph()
        self.network_is_valid  : bool                                      = False

        self._add_node(self._root_node)

    def _add_node(self, name:ConcreteId) -> None:
        """idempotent"""
        match name:
            case x if x is self._root_node:
                self.network.add_node(name)
                self.network.nodes[name][EXPANDED]     = True
                self.network.nodes[name][REACTIVE_ADD] = False
                self._root_node.meta                  |= TaskMeta_f.CONCRETE
            case TaskName() if TaskMeta_f.CONCRETE not in name:
                raise ValueError("Nodes should only be instantiated spec names", name)
            case _ if name in self.network.nodes:
                return
            case TaskArtifact():
                # Add node with metadata
                logging.debug("Inserting Artifact into network: %s", name)
                self.network.add_node(name)
                self.network.nodes[name][EXPANDED]     = False
                self.network.nodes[name][REACTIVE_ADD] = False
                self.network_is_valid = False
            case TaskName():
                # Add node with metadata
                logging.debug("Inserting ConcreteId into network: %s", name)
                self.network.add_node(name)
                self.network.nodes[name][EXPANDED]     = False
                self.network.nodes[name][REACTIVE_ADD] = False
                self.network_is_valid = False

    def _match_artifact_to_transformers(self, artifact:TaskArtifact) -> set[TaskName]:
        """
          Match and instantiate artifact transformers when applicable
          filters out transformers which are already connected to the artifact.
        """
        logging.debug("-- Instantiating Artifact Relevant Transformers")
        assert(artifact in self.network.nodes)
        to_expand              = set()
        available_transformers = set()
        local_nodes            = set()
        local_nodes.update(self.network.pred[artifact].keys())
        local_nodes.update(self.network.succ[artifact].keys())

        # ignore unrelated artifacts
        def abstraction_test(x) -> bool:
            return artifact in x and x in self._transformer_specs

        for abstract in [x for x in self._abstract_artifacts if abstraction_test(x)]:
            # And get transformers of related artifacts
            available_transformers.update(self._transformer_specs[abstract])

        filtered = (available_transformers - local_nodes)
        logging.debug("Transformers: %s available, %s local nodes, %s when filtered", len(available_transformers), len(local_nodes), len(filtered))
        for transformer in filtered:
            if bool(local_nodes.intersection(self.concrete[transformer])):
                continue
            match self._instantiate_transformer(transformer, artifact):
                case None:
                    pass
                case TaskName() as instance:
                    logging.debug("-- Matching Transformer found: %s", transformer)
                    spec = self.specs[instance]
                    # A transformer *always* has at least 1 dependency and requirement,
                    # which is *always* the updated artifact relations
                    if spec.depends_on[-1].target == artifact:
                        self.connect(artifact, instance)
                    elif spec.required_for[-1].target == artifact:
                        self.connect(instance, artifact)
                    else:
                        raise ValueError("instantiated a transformer that doesn't match the artifact which triggered it", artifact, spec)

                    to_expand.add(instance)

        return to_expand

    def _expand_task_node(self, name:ConcreteId) -> set[ConcreteId]:
        """ expand a task node, instantiating and connecting to its dependencies and dependents,
        *without* expanding those new nodes.
        returns a list of the new nodes tasknames
        """
        assert(TaskMeta_f.CONCRETE in name)
        assert(not self.network.nodes[name].get(EXPANDED, False))
        spec                                                  = self.specs[name]
        spec_pred, spec_succ                                  = self.network.pred[name], self.network.succ[name]
        indirect_deps : list[tuple[ConcreteId, RelationSpec]] = self._requirements[spec.sources[-1]]
        to_expand                                             = set()

        logging.debug("--> Expanding Task: %s : Pre(%s), Post(%s), IndirecPre:(%s)",
                      name, len(spec.depends_on), len(spec.required_for), len(indirect_deps))
        # (maybe) Connect a jobs $head$
        to_expand.update(self._expand_job_head(spec))
        # Connect Relations
        for rel in itz.chain(spec.action_group_elements(), indirect_deps):
            if not isinstance(rel, RelationSpec):
                continue
            relevant_edges = spec_succ if rel.forward_dir_p() else spec_pred
            match rel:
                case RelationSpec(target=TaskArtifact() as target):
                    assert(target in self.artifacts)
                    self.connect(*rel.to_edge(name))
                    to_expand.add(target)
                case RelationSpec(target=TaskName()) if rel.match_simple_edge(relevant_edges.keys(), exclude=[name]):
                    # already linked, ignore.
                    continue
                case RelationSpec(target=TaskName()):
                    # Get specs and instances with matching target
                    instance = self._instantiate_relation(rel, control=name)
                    self.connect(*rel.to_edge(name, instance=instance))
                    to_expand.add(instance)
        else:
            assert(name in self.network.nodes)
            self.network.nodes[name][EXPANDED] = True


        logging.debug("<-- Task Expansion Complete: %s", name)
        return to_expand

    def _expand_job_head(self, spec:TaskSpec) -> list[TaskName]:
        """

        """
        if TaskMeta_f.JOB not in spec.name:
            return []

        logging.debug("Expanding Job Head for: %s", spec.name)
        head_name = spec.job_head_name()
        head_instance = self._instantiate_spec(head_name, extra=spec.model_extra)
        self.connect(spec.name, head_instance)
        return [head_instance]

    def _expand_artifact(self, artifact:TaskArtifact) -> set[ConcreteId]:
        """ expand artifacts, instantaiting related tasks/transformers,
          and connecting the task to its abstract/concrete related artifacts
          """
        assert(artifact in self.artifacts)
        assert(artifact in self.network.nodes)
        assert(not self.network.nodes[artifact].get(EXPANDED, False))
        logging.debug("--> Expanding Artifact: %s", artifact)
        to_expand = set()

        logging.debug("-- Instantiating Artifact relevant tasks")
        for name in self.artifacts[artifact]:
            instance = self._instantiate_spec(name)
            # Don't connect it to the network, it'll be expanded later
            self.connect(instance, False)
            to_expand.add(instance)

        to_expand.update(self._match_artifact_to_transformers(artifact))

        match artifact.is_concrete:
            case True:
                logging.debug("-- Connecting concrete artifact to parent abstracts")
                for abstract in [x for x in self._abstract_artifacts if artifact in x and LocationMeta_f.glob in x]:
                    self.connect(artifact, abstract)
                    to_expand.add(abstract)
            case False:
                logging.debug("-- Connecting abstract task to child concrete artifacts")
                for conc in [x for x in self._concrete_artifacts if x in artifact]:
                    assert(conc in artifact)
                    self.connect(conc, artifact)
                    to_expand.add(conc)

        logging.debug("<-- Artifact Expansion Complete: %s", artifact)
        self.network.nodes[artifact][EXPANDED] = True
        return to_expand

    def concrete_edges(self, name:ConcreteId) -> tomlguard.TomlGuard:
        """ get the concrete edges of a task.
          ie: the ones in the task network, not the abstract ones in the spec.
        """
        assert(name in self.network)
        preds = self.network.pred[name]
        succ  = self.network.succ[name]
        return tomlguard.TomlGuard({
            "pred" : {"tasks": [x for x in preds if isinstance(x, TaskName)],
                      "artifacts": {"abstract": [x for x in preds if isinstance(x, TaskArtifact) and not x.is_concrete],
                                    "concrete": [x for x in preds if isinstance(x, TaskArtifact) and x.is_concrete]}},
            "succ" : {"tasks": [x for x in succ  if isinstance(x, TaskName) and x is not self._root_node],
                      "artifacts": {"abstract": [x for x in succ if isinstance(x, TaskArtifact) and not x.is_concrete],
                                    "concrete": [x for x in succ if isinstance(x, TaskArtifact) and x.is_concrete]}},
            "root" : self._root_node in succ,
            })

    def connect(self, left:None|ConcreteId, right:None|False|ConcreteId=None) -> None:
        """
        Connect a task node to another. left -> right
        If given left, None, connect left -> ROOT
        if given left, False, just add the node
        """
        self.network_is_valid = False
        match left:
            case TaskName() if left not in self.specs:
                raise doot.errors.DootTaskTrackingError("Can't connect a non-existent task", left)
            case TaskArtifact() if left not in self.artifacts:
                raise doot.errors.DootTaskTrackingError("Can't connect a non-existent artifact", left)
            case _ if left not in self.network.nodes:
                self._add_node(left)

        match right:
            case False:
                return
            case None:
                right = self._root_node
            case TaskName() if right not in self.specs:
                raise doot.errors.DootTaskTrackingError("Can't connect a non-existent task", right)
            case TaskArtifact() if right not in self.artifacts:
                raise doot.errors.DootTaskTrackingError("Can't connect a non-existent artifact", right)
            case _ if right not in self.network.nodes:
                self._add_node(right)

        if right in self.network.succ[left]:
            # nothing to do
            return

        logging.debug("Connecting: %s -> %s", left, right)
        # Add the edge, with metadata
        match left, right:
            case TaskName(), TaskName():
                self.network.add_edge(left, right, type=EdgeType_e.TASK)
            case TaskName(), TaskArtifact():
                self.network.add_edge(left, right, type=EdgeType_e.TASK_CROSS)
            case TaskArtifact(), TaskName():
                self.network.add_edge(left, right, type=EdgeType_e.ARTIFACT_CROSS)
            case TaskArtifact(), TaskArtifact() if left.is_concrete and right.is_concrete:
                raise doot.errors.DootTaskTrackingError("Tried to connect two concrete artifacts", left, right)
            case TaskArtifact(), TaskArtifact() if right.is_concrete:
                self.network.add_edge(left, right, type=EdgeType_e.ARTIFACT_UP)
            case TaskArtifact(), TaskArtifact() if not right.is_concrete:
                self.network.add_edge(left, right, type=EdgeType_e.ARTIFACT_DOWN)

    def validate_network(self) -> bool:
        """ Finalise and ensure consistence of the task network.
        run tests to check the dependency graph is acceptable
        """
        logging.debug("Validating Task Network")
        if not nx.is_directed_acyclic_graph(self.network):
            raise doot.errors.DootTaskTrackingError("Network isn't a DAG")

        for node, data in self.network.nodes.items():
            match node:
                case TaskName() | TaskArtifact() if not data[EXPANDED]:
                    raise doot.errors.DootTaskTrackingError("Network isn't fully expanded", node)
                case TaskName() if TaskMeta_f.CONCRETE not in node:
                    raise doot.errors.DootTaskTrackingError("Abstract ConcreteId in network", node)
                case TaskArtifact() if LocationMeta_f.glob in node:
                    bad_nodes = [x for x in self.network.pred[node] if x in self.specs]
                    if bool(bad_nodes):
                        raise doot.errors.DootTaskTrackingError("Glob Artifact ConcreteId is a successor to a task", node, bad_nodes)

    def incomplete_dependencies(self, focus:ConcreteId) -> list[ConcreteId]:
        """ Get all predecessors of a node that don't evaluate as complete """
        assert(focus in self.network.nodes)
        incomplete = []
        for x in [x for x in self.network.pred[focus] if self.get_status(x) not in TaskStatus_e.success_set]:
            match x:
                case TaskName() if x not in self.tasks:
                    incomplete.append(x)
                case TaskName() if not bool(self.tasks[x]):
                    incomplete.append(x)
                case TaskArtifact() if not bool(x):
                    incomplete.append(x)

        return incomplete

    def build_network(self, *, sources:None|list[ConcreteId]=None) -> None:
        """
        for each task queued (ie: connected to the root node)
        expand its dependencies and add into the network, until no mode nodes to expand.
        then connect concerete artifacts to abstract artifacts.

        # TODO network could be built in total, or on demand
        """
        logging.debug("-> Building Task Network")
        match sources:
            case None:
                queue = list(self.network.pred[self._root_node].keys())
            case [*xs]:
                queue = list(sources)
        processed = { self._root_node }
        logging.info("Initial Network Queue: %s", queue)
        while bool(queue): # expand tasks
            logging.debug("- Processing: %s", queue[-1])
            match (current:=queue.pop()):
                case x if x in processed or self.network.nodes[x].get(EXPANDED, False):
                    logging.debug("- Processed already")
                    processed.add(x)
                case TaskName() as x:
                    additions = self._expand_task_node(x)
                    logging.debug("- Task Expansion produced: %s", additions)
                    queue    += additions
                    processed.add(x)
                case TaskArtifact() as x:
                    additions = self._expand_artifact(x)
                    logging.debug("- Artifact Expansion produced: %s", additions)
                    queue += additions
                    processed.add(x)
                case _:
                    raise ValueError("Unknown value in network")

        else:
            logging.debug("- Final Network Nodes: %s", self.network.nodes)
            logging.debug("<- Final Network Edges: %s", self.network.edges)
            self.network_is_valid = True
            pass
