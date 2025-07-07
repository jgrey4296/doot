#!/usr/bin/env python3
"""
The network of task relations.

Uses an nx.Digraph internally.
Is build 'backwards', as this preserves the meaning
of graph.pred[x]  = [y] as y.depends_on[x]
and graph.succ[x] = [y] as y.required_for[x]

"""
# ruff: noqa: ERA001
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
from ._interface import EdgeType_e
from doot.workflow import ActionSpec, TaskName, TaskSpec, DootTask, RelationSpec, TaskArtifact
# ##-- end 1st party imports

import matplotlib.pyplot as plt
from . import _interface as API # noqa: N812
from doot.workflow._interface import TaskName_p, Artifact_i, RelationSpec_i

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
    import weakref
    from doot.workflow._interface import TaskStatus_e, ArtifactStatus_e
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from .track_registry import TrackRegistry
    from doot.worfklow._interface import TaskSpec_i

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

show_graph : Final[bool] = doot.config.on_fail(False, bool).settings.commands.run.show() # type: ignore[attr-defined]  # noqa: FBT003

DRAW_OPTIONS : Final[dict]  = dict(
    with_labels=True,
    # arrowstyle="->",
    node_color="green",
    verticalalignment="baseline",
    bbox={"edgecolor": "k", "facecolor": "white", "alpha": 0.5 },
)
##--|

class _Expansion_m:

    _tracker  : API.WorkflowTracker_i
    pred      : Mapping
    succ      : Mapping
    nodes     : Mapping
    edges     : Mapping
    _graph    : Any
    non_expanded : set

    def build_network(self, *, sources:Maybe[Literal[True]|list[Concrete[TaskName_p]|Artifact_i]]=None) -> None:
        """
        for each task queued (ie: connected to the root node)
        expand its dependencies and add into the _graph, until no more nodes to expand.
        then connect concrete _tracker._registry.artifacts to abstract _tracker._registry.artifacts.

        passing sources=True forces build of any non_expanded nodes that have an edge

        # TODO _graph could be built in total, or on demand
        """
        x          : Any
        processed  : set
        queue      : list
        additions  : set
        ##--|
        logging.info("[Network.Build] -> Start")
        match sources:
            case None:
                queue = list(self.pred[self._tracker._root_node].keys())
            case True:
                queue_set = set(self.nodes.keys())
                queue_set.update([x for x in self.non_expanded if self.pred[x] or self.succ[x]])
                queue = list(queue_set)
            case [*xs]:
                queue = list(sources)
            case x:
                raise TypeError(type(x))
        processed = { self._tracker._root_node }
        logging.info("[Build.Initial] Network Queue: %s", queue)
        while bool(queue): # expand tasks
            match (current:=queue.pop()):
                case x if x in processed or self.nodes[x].get(API.EXPANDED, False):
                    logging.debug("[Build.Processed] %s", current)
                    processed.add(x)
                case TaskName_p() as x if x in self.nodes:
                    additions = self._expand_task_node(x)
                    queue    += additions
                    processed.add(x)
                case Artifact_i() as x if x in self.nodes:
                    additions = self._expand_artifact(x)
                    logging.debug("[Build.Artifact] Expansion produced: %s", additions)
                    queue += additions
                    processed.add(x)
                case _:
                    raise doot.errors.TrackingError("Unknown value in _graph")

        else:
            logging.debug("[Network.Build] <- Nodes: %s Edges: %s", len(self.nodes), len(self.edges))
            self.report_tree() # type: ignore[attr-defined]

    def connect(self, left:Concrete[TaskName_p]|Artifact_i, right:Maybe[Literal[False]|Concrete[TaskName_p]|Artifact_i]=None, **kwargs) -> None:  # noqa: ANN003
        """
        Connect a task node to another. left -> right
        If given left, None, connect left -> API.ROOT
        if given left, False, just add the node

        (This preserves graph.pred[x] as the nodes x is dependent on)
        """
        assert("type" not in kwargs)
        self._add_node(left)
        match right:
            case False:
                return
            case None:
                right = self._tracker._root_node
                self._add_node(right)
            case x:
                self._add_node(right)


        if left in self.succ and right in self.succ[left]:
            # nothing to do
            return

        # Add the edge, with metadata
        match left, right:
            case TaskName_p(), TaskName_p():
                logging.debug("[Connect] %s -> %s", left, right)
                self._graph.add_edge(left, right, type=EdgeType_e.TASK, **kwargs)
            case TaskName_p(), Artifact_i():
                logging.debug("[Connect] %s -> %s", left[:], right)
                self._graph.add_edge(left, right, type=EdgeType_e.TASK_CROSS, **kwargs)
            case Artifact_i(), TaskName_p():
                logging.debug("[Connect] %s -> %s", left, right[:])
                self._graph.add_edge(left, right, type=EdgeType_e.ARTIFACT_CROSS, **kwargs)
            case Artifact_i(), Artifact_i() if left.is_concrete() and right.is_concrete():
                raise doot.errors.TrackingError("Tried to connect two concrete _tracker._registry.artifacts", left, right)
            case Artifact_i(), Artifact_i() if right.is_concrete():
                logging.debug("[Connect] %s -> %s", left, right)
                self._graph.add_edge(left, right, type=EdgeType_e.ARTIFACT_UP, **kwargs)
            case Artifact_i(), Artifact_i() if not right.is_concrete():
                logging.debug("[Connect] %s -> %s", left, right)
                self._graph.add_edge(left, right, type=EdgeType_e.ARTIFACT_DOWN, **kwargs)

    ##--| internal

    def _add_node(self, name:Concrete[TaskName_p]|Artifact_i) -> None:
        """idempotent"""
        match name:
            case x if x in self.nodes:
                return
            case x if x is self._tracker._root_node:
                if x in self._graph:
                    return
                self._graph.add_node(name)
                self.nodes[name][API.EXPANDED]     = True
                self.nodes[name][API.REACTIVE_ADD] = False
            case TaskName_p() as x if not x.uuid():
                raise doot.errors.TrackingError("Nodes should only be instantiated spec names", x)
            case TaskName_p() as x if x not in self._tracker.specs:
                raise doot.errors.TrackingError("Can't connect a non-existent task", x)
            case Artifact_i() as x if x not in self._tracker.artifacts:
                raise doot.errors.TrackingError("Can't connect a non-existent artifact", x)
            case Artifact_i(): # Add node with metadata
                logging.debug("[Network.Artifact.+] %s", name)
                self._graph.add_node(name)
                self.nodes[name][API.EXPANDED]      = False
                self.nodes[name][API.REACTIVE_ADD]  = False
                self.non_expanded.add(name)
            case TaskName_p():  # Add node with metadata
                logging.debug("[Network.Task.+] %s", name)
                self._graph.add_node(name)
                self.nodes[name][API.EXPANDED]      = False
                self.nodes[name][API.REACTIVE_ADD]  = False
                self.non_expanded.add(name)
            case x:
                raise TypeError(type(x))

    def _expand_task_node(self, name:Concrete[TaskName_p]) -> set[Concrete[TaskName_p]|Artifact_i]:
        """ expand a task node, instantiating and connecting to its dependencies and dependents,
        *without* expanding those new nodes.
        returns a list of the new nodes tasknames
        """
        to_expand  : set[TaskName_p|Artifact_i]
        spec       : TaskSpec_i
        assert(name.uuid())
        assert(not self.nodes[name].get(API.EXPANDED, False))
        spec                 = self._tracker.specs[name].spec
        spec_pred, spec_succ = self.pred[name], self.succ[name]
        to_expand            = set()

        logging.info("[Build.Expand.Task] -> %s : Pre(%s), Post(%s)", name, len(spec.depends_on), len(spec.required_for))

        # Connect Relations
        for rel in self._tracker._factory.action_group_elements(spec):
            if not isinstance(rel, RelationSpec_i):
                # Ignore Actions
                continue
            relevant_edges = spec_succ if rel.forward_dir_p() else spec_pred
            match rel:
                case RelationSpec_i(target=Artifact_i() as target):
                    # Connect the artifact mentioned
                    assert(target in self._tracker.artifacts)
                    self.connect(*rel.to_ordered_pair(name)) # type: ignore[arg-type]
                    to_expand.add(target)
                case RelationSpec_i(target=TaskName_p() as target) if target.is_head() and target not in self._tracker.specs:
                    pass
                case RelationSpec_i(target=TaskName_p() as target) if target.is_cleanup() and target not in self._tracker.specs:
                    pass
                case RelationSpec_i(target=TaskName_p() as target):
                    # Get specs and instances with matching target
                    instance = self._tracker._instantiate(rel, control=name)
                    self.connect(*rel.to_ordered_pair(name, target=instance)) # type: ignore[arg-type]
                    to_expand.add(instance)
        else:
            assert(name in self.nodes)
            self.nodes[name][API.EXPANDED] = True
            self.non_expanded.remove(name)

        to_expand.update(self._generate_successor_nodes(spec))
        logging.debug("[Build.Expand.Task] <- %s : %s", name, to_expand)
        return to_expand

    def _generate_successor_nodes(self, spec:Concrete[TaskSpec]) -> list[Concrete[TaskName_p]]:
        """
          instantiate and connect a job's head task

        for a spec S, find the tasks T that have registered a relation
        of T < S.
        (S would not know about these blockers).

        For these T, link instantiated nodes that match constraints and link them to S,
        or if no nodes exist, create and link them.
        """
        result = []
        logging.debug("[Build.Task.Successor] : %s", spec.name)
        names = self._tracker._subfactory.generate_names(spec)
        assert(len(names) <= 1)
        for x in names:
            logging.debug("[Successor] : %s", x)
            assert(x.uuid() == spec.name.uuid())
            assert(x in self._tracker.specs)
            self.connect(spec.name, x)
            result.append(x)
        else:
            return result

    def _expand_artifact(self, artifact:Artifact_i) -> set[Concrete[TaskName_p]|Artifact_i]:
        """ expand _tracker._registry.artifacts, instantiating related tasks,
          and connecting the task to its abstract/concrete related _tracker._registry.artifacts
          """
        to_expand  : set[TaskName_p|Artifact_i]
        meta       : API.ArtifactMeta_d
        abstract   : TaskName_p | Artifact_i
        ##--|
        assert(artifact in self._tracker.artifacts)
        assert(artifact in self.nodes)
        assert(not self.nodes[artifact].get(API.EXPANDED, False))
        logging.info("[Build.Expand.Artifact] --> %s", artifact)
        to_expand  = set()

        meta       = self._tracker.artifacts[artifact]
        relevant   = list(meta.builders)
        logging.debug("-- Instantiating Artifact relevant tasks: %s", len(relevant))
        for name in relevant:
            instance = self._tracker._instantiate(name)
            assert(instance is not None)
            self.connect(instance, False)  # noqa: FBT003
            to_expand.add(instance)

        match artifact.is_concrete():
            case True:
                logging.debug("-- Connecting concrete artifact to parent abstracts")
                art_path = DKey[pl.Path](artifact[1,:])(relative=True) # type: ignore[operator]
                for abstract in self._tracker.abstract:
                    match abstract:
                        case TaskName_p():
                            continue
                        case Artifact_i() as x if art_path not in x and artifact not in x:
                            continue
                        case _:
                            self.connect(artifact, abstract)
                            to_expand.add(abstract)
            case False:
                logging.debug("-- Connecting abstract task to child concrete _tracker._registry.artifacts")
                for conc in self._tracker.concrete:
                    match conc:
                        case TaskName_p():
                            continue
                        case Artifact_i():
                            assert(conc.is_concrete())
                            conc_path = DKey[pl.Path](conc[1,:])(relative=True) # type: ignore[operator]
                            if conc_path not in artifact:
                                continue
                            self.connect(conc, artifact)
                            to_expand.add(conc)

        logging.info("[Build.Expand.Artifact] <-- %s -> %s", artifact, to_expand)
        self.nodes[artifact][API.EXPANDED] = True
        self.non_expanded.remove(artifact)
        return to_expand

class _Validation_m:

    _tracker  : API.WorkflowTracker_i
    _graph    : Any
    nodes     : Mapping
    edges     : Mapping
    pred      : Mapping
    succ      : Mapping

    def validate_network(self, *, strict:bool=True) -> bool:            # noqa: PLR0912
        """ Finalise and ensure consistence of the task _graph.
        run tests to check the dependency graph is acceptable
        """
        logging.info("Validating Task Network")
        if not nx.is_directed_acyclic_graph(self._graph):
            raise doot.errors.TrackingError("Network isn't a DAG")

        failures = []
        for node, data in self.nodes.items():
            match node:
                case TaskName_p() as x if x == self._tracker._root_node:  # Ignore the root
                    pass
                case TaskName_p():
                    if not data.get(API.EXPANDED, False):               # every node is expanded
                        failures.append(f"{node} is not expanded")
                    if not node.uuid():                                 # every node is uniq
                        failures.append(f"{node} is not unique")
                    if node not in self._tracker.specs:                 # every node has a spec
                        failures.append(f"{node} has no backing spec")
                case Artifact_i():
                    if not data.get(API.EXPANDED, False):               # Every node is expanded
                        failures.append(f"{node} is not expanded")
                    if (TaskArtifact.Wild.glob in node
                        and not bool(self._graph.pred[node])):
                        failures.append(f"{node} has no concrete predecessors")
        else:
            if not self._tracker.is_valid:
                raise doot.errors.TrackingError("Network is not marked as valid")

            if not bool(failures):
                return True

            if strict:
                raise doot.errors.TrackingError("Errors in network", failures)
            else:
                logging.warning("Failures in network: %s", failures)
                return False

    def concrete_edges(self, name:Concrete[TaskName_p|TaskArtifact]) -> ChainGuard:
        """ get the concrete edges of a task.
          ie: the ones in the task _graph, not the abstract ones in the spec.
        """
        assert(name in self.nodes)
        preds = self.pred[name]
        succ  = self.succ[name]
        return ChainGuard({
            "pred" : {"tasks": [x for x in preds if isinstance(x, TaskName)],
                      "_tracker._registry.artifacts": {"abstract": [x for x in preds if isinstance(x, TaskArtifact) and not x.is_concrete()],
                                    "concrete": [x for x in preds if isinstance(x, TaskArtifact) and x.is_concrete()]}},
            "succ" : {"tasks": [x for x in succ  if isinstance(x, TaskName) and x is not self._tracker._root_node],
                      "_tracker._registry.artifacts": {"abstract": [x for x in succ if isinstance(x, TaskArtifact) and not x.is_concrete()],
                                    "concrete": [x for x in succ if isinstance(x, TaskArtifact) and x.is_concrete()]}},
            "root" : self._tracker._root_node in succ,
            })

    def report_tree(self) -> None:
        mapping : dict[TaskName_p|Artifact_i, str]
        if not show_graph:
            return

        mapping = {}
        count = 0
        for x in self._graph.nodes:
            match x:
                case Artifact_i():
                    mapping[x] = str(x)
                case TaskName_p():
                    mapping[x] = f"{x[:]}.{count}"
                    count += 1

        mapping[self._tracker._root_node] = cast("str", self._tracker._root_node)
        undir = nx.Graph(self._graph)
        undir = nx.relabel_nodes(undir, mapping)

        sub = undir.subgraph(nx.node_connected_component(undir, self._tracker._root_node))
        nx.draw(sub, pos=nx.bfs_layout(sub, self._tracker._root_node), **DRAW_OPTIONS)
        plt.show()

##--|

@Mixin(_Expansion_m, _Validation_m)
class TrackNetwork:
    """ The _graph of concrete tasks and their dependencies """
    # TODO use this instaed of _tracker._registry
    _tracker      : API.WorkflowTracker_p
    _graph        : nx.DiGraph[Concrete[TaskName_p]|TaskArtifact]

    non_expanded  : set[TaskName_p|Artifact_i]
    def __init__(self, *, tracker:API.WorkflowTracker_p) -> None:
        match tracker:
            case API.WorkflowTracker_p():
                self._tracker = tracker
            case x:
                raise TypeError(type(x))
        self._graph        = nx.DiGraph()
        self.non_expanded  = set()
        self._add_node(self._tracker._root_node)  # type: ignore[attr-defined]


    ##--| properties

    @property
    def nodes(self) -> dict:
        return self._graph.nodes

    @property
    def edges(self) -> dict:
        return self._graph.edges

    @property
    def pred(self) -> dict:
        return self._graph.pred

    @property
    def adj(self) -> dict:
        return self._graph.adj

    @property
    def succ(self) -> dict:
        return self._graph.succ

    ##--| dunders

    def __len__(self) -> int:
        return len(self._graph.nodes)

    def __contains__(self, other:Concrete[TaskName_p]|TaskArtifact) -> bool:
        return other in self._graph
