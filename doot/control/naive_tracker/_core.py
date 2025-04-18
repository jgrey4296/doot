#!/usr/bin/env python3
"""
Abstract Specs: A[n]
Concrete Specs: C[n]
Task:           T[n]

  Expansion: ∀x ∈ C[n].depends_on => A[x] -> C[x]
  Head: C[1].depends_on[A[n].$head$] => A[n] -> C[n], A[n].head -> C[n].head, connect

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
import boltons.queueutils
import networkx as nx
from jgdv.structs.chainguard import ChainGuard
from jgdv.structs.strang import CodeReference
from jgdv.structs.dkey import DKey
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._structs.relation_spec import RelationSpec
from doot.enums import TaskMeta_e, QueueMeta_e, TaskStatus_e, LocationMeta_e, RelationMeta_e, EdgeType_e, ArtifactStatus_e
from doot.structs import (ActionSpec, TaskArtifact, TaskName, TaskSpec, InjectSpec)
from doot.task.core.task import DootTask
from doot.mixins.matching import TaskMatcher_m
# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, Generic, cast, assert_type, assert_never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
   from jgdv import Maybe, Ident
   from typing import Final
   from typing import ClassVar, Any, LiteralString
   from typing import Never, Self, Literal
   from typing import TypeGuard
   from collections.abc import Iterable, Iterator, Callable, Generator
   from collections.abc import Sequence, Mapping, MutableMapping, Hashable

   type Abstract[T] = T
   type Concrete[T] = T
   type ActionElem  = ActionSpec|RelationSpec
   type ActionGroup = list[ActionElem]

##--|
from doot._abstract import Task_p, TaskTracker_p
# isort: on
# ##-- end types

##-- logging
logging    = logmod.getLogger(__name__)
logging.disabled = False
##-- end logging

ROOT                           : Final[str]                  = "root::_.$gen$" # Root node of dependency graph
EXPANDED                       : Final[str]                  = "expanded"  # Node attribute name
REACTIVE_ADD                   : Final[str]                  = "reactive-add"
ARTIFACT_EDGES                 : Final[set[EdgeType_e]]      = EdgeType_e.artifact_edge_set
DECLARE_PRIORITY               : Final[int]                  = 10
MIN_PRIORITY                   : Final[int]                  = -10
INITAL_SOURCE_CHAIN_COUNT      : Final[int]                  = 10

##--|
class _Registration_m:

    def register_spec(self, *specs:TaskSpec) -> None:
        """ Register task specs, abstract or concrete.
        """
        queue = []
        queue += specs
        while bool(queue):
            spec = queue.pop(0)
            if spec.name in self.specs:
                continue
            if TaskMeta_e.DISABLED in spec.meta:
                doot.report.detail("Ignoring Registration of disabled task: %s", spec.name.readable)
                continue

            self.specs[spec.name] = spec
            logging.detail("Registered Spec: %s", spec.name)

            # Register the abstract head and cleanup tasks
            if spec.name.is_uniq():
                pass
            elif TaskMeta_e.JOB in spec.meta:
                queue += spec.gen_job_head()
            else:
                queue += spec.gen_cleanup_task()

            self._register_artifacts(spec.name)
            self._register_blocking_relations(spec)

    def _register_artifacts(self, name:Concrete[TaskSpec]) -> None:
        """ Register the artifacts in a spec """
        match self.specs.get(name, None):
            case None:
                msg = "Tried to register artifacts of a non-registered spec"
                raise doot.errors.TrackingError(msg, name)
            case x if x.name.is_uniq():
                return
            case x:
                spec = x

        for rel in spec.action_group_elements():
            match rel:
                case RelationSpec(target=TaskArtifact() as art):
                    logging.trace("Registering Artifact Relation: %s, %s", art, spec.name)
                    # Link artifact to its source task
                    self.artifacts[art].add(spec.name)
                    # Add it to the relevant abstract/concrete set
                    match art.is_concrete():
                        case False:
                            self._abstract_artifacts.add(art)
                        case True:
                            self._concrete_artifacts.add(art)
                case _:
                    pass

    def _register_blocking_relations(self, spec:TaskSpec) -> None:
        if spec.name.is_uniq():
            # If the spec is instantiated,
            # it has no indirect relations
            return

        # Register Indirect dependencies:
        # So if spec blocks target,
        # record that target needs spec
        for rel in spec.action_group_elements():
            match rel:
                case RelationSpec(target=target, relation=RelationMeta_e.blocks):
                    logging.trace("Registering Indirect Relation: %s %s", spec.name, rel)
                    rel.object = spec.name
                    self._indirect_deps[target].append(rel)
                case _: # Ignore action specs
                    pass

class _Instantiation_m:

    def _maybe_reuse_instantiation(self, name:TaskName, *, add_cli:bool=False, extra:bool=False) -> Maybe[Concrete[Ident]]:
        """ if an existing concrete spec exists, use it if it has no conflicts """
        if name.is_uniq():
            logging.detail("Not reusing instantiation because name is concrete: %s", name)
            return None
        if name not in self.specs:
            logging.detail("Not reusing instantiation because name doesn't have a matching spec: %s", name)
            return None
        if extra or add_cli:
            logging.detail("Not reusing instantiation because extra or cli args were requested: %s", name)
            return None

        if not bool(self.concrete[name]):
            logging.detail("Not reusing instantiation because there is no instantiation to reuse: %s", name)
            return None

        abstract = self.specs[name]
        match [x for x in self.concrete[name] if abstract != (concrete:=self.specs[x]) and self.match_with_constraints(concrete, abstract)]:
            case []:
                logging.detail("Not reusing instantiation because existing specs dont match with constraints: %s", name)
                return None
            case [x, *xs]:
                logging.detail("Reusing Concrete Spec: %s for %s", x, name)
                # Can use an existing concrete spec
                return x

    def _get_task_source_chain(self, name:Abstract[Ident]) -> list[Abstract[TaskSpec]]:
        """ get the chain of sources for a task.
          this traces from an instance back towards the root,
          returning [root, ... grandparent, parent, instance].

          traces with the *last* value in spec.sources.
        """
        spec                                 = self.specs[name]
        source_chain   : list[TaskSpec]      = []
        current        : None|TaskSpec       = spec
        count          : int                 = INITAL_SOURCE_CHAIN_COUNT
        while current is not None:
            if 0 > count:
                raise doot.errors.TrackingError("Building a source chain grew to large", name)
            count -= 1
            match current: # Determine the base
                case TaskSpec(name=name) if TaskName.bmark_e.head in name:
                    # job heads are generated, so don't have a source chain
                    source_chain.append(current)
                    current = None
                case TaskSpec(sources=[pl.Path()]|[]):
                    source_chain.append(current)
                    current = None
                case TaskSpec(sources=[*xs, TaskName() as src]):
                    source_chain.append(current)
                    current = self.specs.get(src, None)
                case TaskSpec(sources=[*xs, None]):
                    # Stop the chain search
                    source_chain.append(current)
                    current = None
                case _:
                    raise doot.errors.TrackingError("Unknown spec customization attempt", spec, current, source_chain)

        source_chain.reverse()
        return source_chain

    def _instantiate_spec(self, name:Abstract[Ident], *, add_cli:bool=False, extra:Maybe[dict|ChainGuard]=None) -> Concrete[Ident]:
        """ Convert an Asbtract Spec into a Concrete Spec,
          Reuses a existing concrete spec if possible.
          """
        match self._maybe_reuse_instantiation(name, add_cli=add_cli, extra=bool(extra)):
            case None:
                pass
            case TaskName() as existing:
                doot.report.trace("Reusing instantiation: %s for %s", existing, name)
                return existing

        spec = self.specs[name]
        # Instantiate the spec from its source chain
        match self._get_task_source_chain(name):
            case []:
                # There should always be a source for a spec
                raise doot.errors.TrackingError("this shouldn't be possible", name)
            case [x]:
                # No chain, just instantiate the spec
                instance_spec = x.instantiate_onto(None)
            case [*xs]:
                # (reversed because the chain goes from spec -> ancestor)
                # and you want to instantiate descendents onto ancestors
                instance_spec = ftz.reduce(lambda x, y: y.instantiate_onto(x), xs)

        logging.trace("Instantiating: %s into %s", name, instance_spec.name)
        assert(instance_spec is not None)
        if add_cli:
            # only add cli args explicitly. ie: when the task has been queued by the user
            instance_spec = instance_spec.apply_cli_args()

        if extra:
            # apply additional settings onto the instance
            instance_spec = instance_spec.specialize_from(extra)

        assert(instance_spec.name.is_uniq())
        # Map abstract -> concrete
        self.concrete[name].append(instance_spec.name)
        # register the actual concrete spec
        self.register_spec(instance_spec)

        assert(instance_spec.name in self.specs)
        return instance_spec.name

    def _instantiate_relation(self, rel:RelationSpec, *, control:Concrete[Ident]) -> Concrete[Ident]:
        """ find a matching relendency/requirement according to a set of keys in the spec, or create a matching instance
          if theres no constraints, will just instantiate.
          """
        logging.trace("Instantiating Relation: %s - %s -> %s", control, rel.relation.name, rel.target)
        if control not in self.specs:
            raise doot.errors.TrackingError("Relation Control is missing from registered specs", control, rel)
        if rel.target not in self.specs:
            raise doot.errors.TrackingError("Relation Target is missing from registered specs", rel.target, control, rel)

        control_spec              = self.specs[control]
        target_spec               = self.specs[rel.target]
        successful_matches        = []
        try:
            match InjectSpec.build(rel, sources=[control_spec]):
                case None:
                    extra = {}
                case x:
                    extra     : dict       = x.as_dict(constraint=target_spec)
        except doot.errors.InjectionError as err:
            raise doot.errors.TrackingError(*err.args, control, rel) from None
        except TypeError as err:
            raise doot.errors.TrackingError(*err.args, control, rel) from None

        # Get and test existing concrete specs to see if they can be reused
        match self.concrete.get(rel.target, None):
            case [] | None if rel.target not in self.specs:
                raise doot.errors.TrackingError("Unknown target declared in Constrained Relation", control, rel.target)
            case [] | None:
                pass
            case [*xs]:
                # concrete instances exist, match on them
                potentials : list[TaskSpec] = [self.specs[x] for x in xs]
                successful_matches += [x.name for x in potentials if self.match_with_constraints(x, control_spec, relation=rel)]

        match successful_matches:
            case []: # No matches, instantiate new
                instance  : TaskName   = self._instantiate_spec(rel.target, extra=extra)
                if not self.match_with_constraints(self.specs[instance], control_spec, relation=rel):
                    raise doot.errors.TrackingError("Failed to build task matching constraints", str(control_spec.name), str(instance), rel)
                logging.detail("Using New Instance: %s", instance)
                return instance
            case [x]: # One match, connect it
                assert(x in self.specs)
                assert(x.is_uniq())
                instance : TaskName = x
                logging.detail("Reusing Instance: %s", instance)
                return instance
            case [*xs, x]: # TODO check this.
                # Use most recent instance?
                assert(x in self.specs)
                assert(x.is_uniq())
                instance : TaskName = x
                logging.detail("Reusing latest Instance: %s", instance)
                return instance

    def _make_task(self, name:Concrete[Ident], *, task_obj:Maybe[Task_p]=None) -> Concrete[Ident]:
        """ Build a Concrete Spec's Task object
          if a task_obj is provided, store that instead

          return the name of the task
          """
        if not isinstance(name, TaskName):
            raise doot.errors.TrackingError("Tried to add a not-task", name)
        if not name.is_uniq():
            raise doot.errors.TrackingError("Tried to add a task using a non-concrete spec", name)
        if name not in self.network.nodes:
            raise doot.errors.TrackingError("Tried to add a non-network task ", name)
        if name in self.tasks:
            return name

        logging.detail("Constructing Task Object: %s", name)
        match task_obj:
            case None:
                spec = self.specs[name]
                try:
                    task : Task_p = spec.make()
                except (ImportError, doot.errors.DootError) as err:
                    raise doot.errors.TrackingError("Failed To Make Task", name, *err.args) from err
            case Task_p():
                task = task_obj
            case _:
                raise doot.errors.TrackingError("Supplied task object isn't a task_i", task_obj)

        # Store it
        self.tasks[name] = task
        return name

@Mixin(_Registration_m, _Instantiation_m, TaskMatcher_m)
class _TrackerStore:
    """ Stores and manipulates specs, tasks, and artifacts """

    # All [Abstract, Concrete] Specs:
    specs                : dict[Ident, TaskSpec]
    # Mapping (Abstract Spec) -> Concrete Specs. Every id, abstract and concerete, has a spec in specs.
    # TODO: Check first entry is always uncustomised
    concrete             : dict[Abstract[Ident], list[Concrete[Ident]]]
    # All (Concrete Specs) Task objects. Invariant: every key in tasks has a matching key in specs.
    tasks                : dict[Concrete[Ident], Task_p]
    # Artifact -> list[TaskName] of related tasks
    artifacts            : dict[TaskArtifact, list[Abstract[Ident]]]
    _artifact_status     : dict[TaskArtifact, ArtifactStatus_e]
    # Artifact sets
    _abstract_artifacts  : set[TaskArtifact]
    _concrete_artifacts  : set[TaskArtifact]
    # indirect requirements from other tasks:
    _indirect_deps       : dict[Concrete[Ident], list[RelationSpec]]


    def __init__(self):
        super().__init__()
        self.specs                = {}
        self.concrete             = defaultdict(lambda: [])
        self.tasks                = {}
        self.artifacts            = defaultdict(set)
        self._artifact_status     = defaultdict(lambda: ArtifactStatus_e.DECLARED)
        self._abstract_artifacts  = set()
        self._concrete_artifacts  = set()
        self._indirect_deps        = defaultdict(lambda: [])

    def get_status(self, task:Concrete[Ident]) -> TaskStatus_e|ArtifactStatus_e:
        """ Get the status of a task or artifact """
        match task:
            case TaskArtifact():
                return self._artifact_status[task]
            case TaskName() if task in self.tasks:
               return self.tasks[task].status
            case TaskName() if task in self.network:
                return TaskStatus_e.DEFINED
            case TaskName() if task in self.specs:
                return TaskStatus_e.DECLARED
            case _:
                return TaskStatus_e.NAMED

    def set_status(self, task:Concrete[Ident]|Task_p, status:TaskStatus_e|ArtifactStatus_e) -> bool:
        """ update the state of a task in the dependency graph
          Returns True on status update,
          False on no task or artifact to update.
        """
        logging.trace("Updating State: %s -> %s", task, status)
        match task, status:
            case TaskName(), _ if task == self._root_node:
                return False
            case Task_p(), TaskStatus_e() if task.name in self.tasks:
                self.tasks[task.name].status = status
            case TaskArtifact(), ArtifactStatus_e():
                self._artifact_status[task] = status
            case TaskName(), TaskStatus_e() if task in self.tasks:
                self.tasks[task].status = status
            case TaskName(), TaskStatus_e():
                logging.detail("Not Setting Status of %s, its hasn't been started", task)
                return False
            case _, _:
                raise doot.errors.TrackingError("Bad task update status args", task, status)

        return True

class _Expansion_m:

    def _expand_task_node(self, name:Concrete[Ident]) -> set[Concrete[Ident]]:
        """ expand a task node, instantiating and connecting to its dependencies and dependents,
        *without* expanding those new nodes.
        returns a list of the new nodes tasknames
        """
        assert(name.is_uniq())
        assert(not self.network.nodes[name].get(EXPANDED, False))
        spec                                                  = self.specs[name]
        spec_pred, spec_succ                                  = self.network.pred[name], self.network.succ[name]
        to_expand                                             = set()

        logging.detail("--> Expanding Task: %s : Pre(%s), Post(%s)", name, len(spec.depends_on), len(spec.required_for))

        to_expand.update(self._expand_generated_tasks(spec))

        logging.trace("Connecting Relations")
        # Connect Relations
        for rel in itz.chain(spec.action_group_elements()):
            if not isinstance(rel, RelationSpec):
                continue
            relevant_edges = spec_succ if rel.forward_dir_p() else spec_pred
            match rel:
                case RelationSpec(target=TaskArtifact() as target):
                    assert(target in self.artifacts)
                    self.connect(*rel.to_ordered_pair(name))
                    to_expand.add(target)
                case RelationSpec(target=TaskName()) if self.match_edge(rel, relevant_edges.keys(), exclude=[name]):
                    # already linked, ignore.
                    continue
                case RelationSpec(target=TaskName()):
                    # Get specs and instances with matching target
                    instance = self._instantiate_relation(rel, control=name)
                    self.connect(*rel.to_ordered_pair(name, target=instance))
                    to_expand.add(instance)
        else:
            assert(name in self.network.nodes)
            self.network.nodes[name][EXPANDED] = True

        logging.detail("<-- Task Expansion Complete: %s", name)
        to_expand.update(self._expand_indirect_relations(spec))

        return to_expand

    def _expand_indirect_relations(self, spec:TaskSpec) -> list[TaskName]:
        """ for a spec S, find the tasks T that have registered a relation
        of T < S.
        (S would not know about these blockers).

        For these T, link instantiated nodes that match constraints and link them to S,
        or if no nodes exist, create and link them.
        """
        to_expand = set()
        spec_pred = self.network.pred[spec.name]
        # Get (abstract) blocking relations from self._indirect_deps
        blockers  = self._indirect_deps[spec.name.pop(top=True)]

        # Try to link instantiated nodes if they match constraints
        # else instantiate and link new nodes

        return to_expand

    def _expand_generated_tasks(self, spec:TaskSpec) -> list[TaskName]:
        """
          instantiate and connect a job's head task
          TODO these could be shifted into the task/job class
        """
        logging.trace("Expanding generated tasks")

        if TaskMeta_e.JOB in spec.meta:
            logging.trace("Generating Job Head for: %s", spec.name)
            head_name = spec.name.de_uniq().with_head()
            head_instance = self._instantiate_spec(head_name, extra=spec.model_extra)
            self.connect(spec.name, head_instance, job_head=True)
            return [head_instance]

        if not spec.name.is_cleanup():
            logging.trace("Generating Cleanup for: %s", spec.name)
            # Instantiate and connect the cleanup task
            cleanup = self._instantiate_spec(spec.name.de_uniq().with_cleanup())
            self.connect(spec.name, cleanup, cleanup=True)
            return [cleanup]

        return []

    def _expand_artifact(self, artifact:TaskArtifact) -> set[Concrete[Ident]]:
        """ expand artifacts, instantiating related tasks,
          and connecting the task to its abstract/concrete related artifacts
          """
        assert(artifact in self.artifacts)
        assert(artifact in self.network.nodes)
        assert(not self.network.nodes[artifact].get(EXPANDED, False))
        logging.trace("Expanding Artifact: %s", artifact)
        to_expand = set()

        logging.trace("Instantiating Artifact relevant tasks")
        for name in self.artifacts[artifact]:
            instance = self._instantiate_spec(name)
            # Don't connect it to the network, it'll be expanded later
            self.connect(instance, False) # noqa: FBT003
            to_expand.add(instance)

        match artifact.is_concrete():
            case True:
                logging.detail("Connecting concrete artifact to dependenct abstracts")
                art_path = DKey(artifact[1:], mark=DKey.Mark.PATH)(relative=True)
                for abstract in self._abstract_artifacts:
                    if art_path not in abstract and artifact not in abstract:
                        continue
                    self.connect(artifact, abstract)
                    to_expand.add(abstract)
            case False:
                logging.detail("Connecting abstract artifact to concrete predecessor artifacts")
                for conc in self._concrete_artifacts:
                    assert(conc.is_concrete())
                    conc_path = DKey(conc[1:], mark=DKey.Mark.PATH)(relative=True)
                    if conc_path not in artifact:
                        continue
                    self.connect(conc, artifact)
                    to_expand.add(conc)

        logging.trace("Expansion Complete: %s", artifact)
        self.network.nodes[artifact][EXPANDED] = True
        return to_expand

@Mixin(_Expansion_m, TaskMatcher_m)
class _TrackerNetwork:
    """ the network of concrete tasks and their dependencies """
    _root_node        : TaskName
    _declare_priority : int
    _min_priority     : int
    network           : nx.DiGraph[Concrete[Ident]]
    network_is_valid  : bool

    def __init__(self):
        super().__init__()
        self._root_node        = TaskName(ROOT)
        self._declare_priority = DECLARE_PRIORITY
        self._min_priority     = MIN_PRIORITY
        self.network           = nx.DiGraph()
        self.network_is_valid  = False

        self._add_node(self._root_node)

    def _add_node(self, name:Concrete[Ident]) -> None:
        """idempotent"""
        match name:
            case x if x is self._root_node:
                self.network.add_node(name)
                self.network.nodes[name][EXPANDED]     = True
                self.network.nodes[name][REACTIVE_ADD] = False
            case TaskName() if not name.is_uniq():
                raise doot.errors.TrackingError("Nodes should only be instantiated spec names", name)
            case _ if name in self.network.nodes:
                return
            case TaskArtifact():
                # Add node with metadata
                logging.trace("Inserting Artifact into network: %s", name)
                self.network.add_node(name)
                self.network.nodes[name][EXPANDED]     = False
                self.network.nodes[name][REACTIVE_ADD] = False
                self.network_is_valid = False
            case TaskName():
                # Add node with metadata
                logging.trace("Inserting Task into network: %s", name)
                self.network.add_node(name)
                self.network.nodes[name][EXPANDED]     = False
                self.network.nodes[name][REACTIVE_ADD] = False
                self.network_is_valid = False

    def concrete_edges(self, name:Concrete[Ident]) -> ChainGuard:
        """ get the concrete edges of a task.
          ie: the ones in the task network, not the abstract ones in the spec.
        """
        assert(name in self.network)
        preds = self.network.pred[name]
        succ  = self.network.succ[name]
        return ChainGuard({
            "pred" : {"tasks": [x for x in preds if isinstance(x, TaskName)],
                      "artifacts": {"abstract": [x for x in preds if isinstance(x, TaskArtifact) and not x.is_concrete()],
                                    "concrete": [x for x in preds if isinstance(x, TaskArtifact) and x.is_concrete()]}},
            "succ" : {"tasks": [x for x in succ  if isinstance(x, TaskName) and x is not self._root_node],
                      "artifacts": {"abstract": [x for x in succ if isinstance(x, TaskArtifact) and not x.is_concrete()],
                                    "concrete": [x for x in succ if isinstance(x, TaskArtifact) and x.is_concrete()]}},
            "root" : self._root_node in succ,
            })

    def connect(self, left:Maybe[Concrete[Ident]], right:Maybe[False|Concrete[Ident]]=None, **kwargs:Any) -> None:
        """
        Connect a task node to another. left -> right
        If given left, None, connect left -> ROOT
        if given left, False, just add the node

        (This preserves graph.pred[x] as the nodes x is dependent on)
        """
        assert("type" not in kwargs)
        self.network_is_valid = False
        match left:
            case x if x == self._root_node:
                pass
            case TaskName() if left not in self.specs:
                raise doot.errors.TrackingError("Can't connect a non-existent task", left)
            case TaskArtifact() if left not in self.artifacts:
                raise doot.errors.TrackingError("Can't connect a non-existent artifact", left)
            case _ if left not in self.network.nodes:
                self._add_node(left)

        match right:
            case False:
                return
            case None:
                right = self._root_node
            case TaskName() if right not in self.specs:
                raise doot.errors.TrackingError("Can't connect a non-existent task", right)
            case TaskArtifact() if right not in self.artifacts:
                raise doot.errors.TrackingError("Can't connect a non-existent artifact", right)
            case _ if right not in self.network.nodes:
                self._add_node(right)

        if right in self.network.succ[left]:
            # nothing to do
            return

        logging.detail("Connecting: %s -> %s", left, right)
        # Add the edge, with metadata
        match left, right:
            case x, y if x == y:
                raise doot.errors.TrackingError("Tried to connect to itself",left,right)
            case TaskName(), TaskName():
                self.network.add_edge(left, right, type=EdgeType_e.TASK, **kwargs)
            case TaskName(), TaskArtifact():
                self.network.add_edge(left, right, type=EdgeType_e.TASK_CROSS, **kwargs)
            case TaskArtifact(), TaskName():
                self.network.add_edge(left, right, type=EdgeType_e.ARTIFACT_CROSS, **kwargs)
            case TaskArtifact(), TaskArtifact() if left.is_concrete() and right.is_concrete():
                raise doot.errors.TrackingError("Tried to connect two concrete artifacts", left, right)
            case TaskArtifact(), TaskArtifact() if right.is_concrete():
                self.network.add_edge(left, right, type=EdgeType_e.ARTIFACT_UP, **kwargs)
            case TaskArtifact(), TaskArtifact() if not right.is_concrete():
                self.network.add_edge(left, right, type=EdgeType_e.ARTIFACT_DOWN, **kwargs)

    def validate_network(self, *, strict:bool=True) -> bool:
        """ Finalise and ensure consistence of the task network.
        run tests to check the dependency graph is acceptable
        """
        logging.trace("Validating Task Network")
        if not nx.is_directed_acyclic_graph(self.network):
            raise doot.errors.TrackingError("Network isn't a DAG")

        for node, data in self.network.nodes.items():
            match node:
                case TaskName() | TaskArtifact() if not data[EXPANDED]:
                    if strict:
                        raise doot.errors.TrackingError("Network isn't fully expanded", node)
                    logging.user("Network Node isn't expanded: %s", node)
                case TaskName() if not node.is_uniq() and node != ROOT:
                    if strict:
                        raise doot.errors.TrackingError("Abstract Concrete[Ident] in network", node)
                    logging.user("Abstract Concrete[Ident] in network: %s", node)
                case TaskArtifact() if LocationMeta_e.abstract in node:
                    # If a node is abtract, it needs to be attacked to something
                    no_ctor = not bool(self.network.pred[node])
                    msg = "Abstract Artifact has no predecessors"
                    if strict and no_ctor:
                        raise doot.errors.TrackingError(msg, node)
                    elif no_ctor:
                        logging.user(msg, node)

    def incomplete_dependencies(self, focus:Concrete[Ident]) -> list[Concrete[Ident]]:
        """ Get all predecessors of a node that don't evaluate as complete """
        assert(focus in self.network.nodes)
        incomplete = []
        for x in self.network.pred[focus]:
            status = self.get_status(x)
            is_success = status in TaskStatus_e.success_set or status is ArtifactStatus_e.EXISTS
            match x:
                case _ if is_success:
                    pass
                case TaskName() if x not in self.tasks:
                    incomplete.append(x)
                case TaskName() if not bool(self.tasks[x]):
                    incomplete.append(x)
                case TaskArtifact() if not bool(x):
                    incomplete.append(x)
        else:
            return incomplete

    def build_network(self, *, sources:Maybe[True|list[Concrete[Ident]]]=None) -> None:
        """
        for each task queued (ie: connected to the root node)
        expand its dependencies and add into the network, until no mode nodes to expand.
        then connect concerete artifacts to abstract artifacts.

        # TODO network could be built in total, or on demand
        """
        logging.trace("-> Building Task Network")
        match sources:
            case None:
                queue = list(self.network.pred[self._root_node].keys())
            case True:
                queue = list(self.network.nodes.keys())
            case [*xs]:
                queue = list(sources)
        processed = { self._root_node }
        logging.detail("Initial Network Queue: %s", queue)
        while bool(queue): # expand tasks
            logging.trace("- Processing: %s", queue[-1])
            match (current:=queue.pop()):
                case x if x in processed or self.network.nodes[x].get(EXPANDED, False):
                    logging.detail("- Processed already")
                    processed.add(x)
                case TaskName() as x if x in self.network.nodes:
                    additions = self._expand_task_node(x)
                    logging.detail("- Task Expansion produced: %s", additions)
                    queue    += additions
                    processed.add(x)
                case TaskArtifact() as x if x in self.network.nodes:
                    additions = self._expand_artifact(x)
                    logging.detail("- Artifact Expansion produced: %s", additions)
                    queue += additions
                    processed.add(x)
                case _:
                    raise doot.errors.TrackingError("Unknown value in network")

        else:
            logging.trace("- Final Network Nodes: %s", self.network.nodes)
            logging.trace("<- Final Network Edges: %s", self.network.edges)
            self.network_is_valid = True
            pass

class _TrackerQueue_boltons:
    """ The _queue of tasks """

    active_set         : list[Concrete[Ident]]
    execution_trace    : list[Concrete[Ident]]
    _queue             : boltons.queueutils.HeapPriorityQueue

    def __init__(self):
        super().__init__()
        self.active_set         = set()
        self.execution_trace    = []
        self._queue             = boltons.queueutils.HeapPriorityQueue()

    def __bool__(self):
        return self._queue.peek(default=None) is not None

    def _maybe_implicit_queue(self, task:Task_p) -> None:
        """ tasks can be activated for running by a number of different conditions
          this handles that
          """
        if task.spec.name in self.active_set:
            return

        match task.spec.queue_behaviour:
            case QueueMeta_e.auto:
                self.queue_entry(task.name)
            case QueueMeta_e.reactive:
                self.network.nodes[task.name][REACTIVE_ADD] = True
            case QueueMeta_e.default:
                # Waits for explicit _queue
                pass
            case _:
                raise doot.errors.TrackingError("Unknown _queue behaviour specified: %s", task.spec.queue_behaviour)

    def _reactive_queue(self, focus:Concrete[Ident]) -> None:
        """ Queue any known task in the network that auto-reacts to a focus """
        for adj in self.network.adj[focus]:
            if self.network.nodes[adj].get(REACTIVE_ADD, False):
                self.queue_entry(adj, silent=True)

    def _reactive_fail_queue(self, focus:Concrete[Ident]) -> None:
        """ TODO: make reactive failure tasks that can be triggered from
          a tasks 'on_fail' collection
          """
        raise NotImplementedError()

    def deque_entry(self, *, peek:bool=False) -> Concrete[Ident]:
        """ remove (or peek) the top task from the _queue .
          decrements the priority when popped.
        """
        if peek:
            return self._queue.peek()

        match self._queue.pop():
            case TaskName() as focus if self.tasks[focus].priority < self._min_priority:
                logging.user("Task halted due to reaching minimum priority while tracking: %s", focus)
                self.set_status(focus, TaskStatus_e.HALTED)
            case TaskName() as focus:
                self.tasks[focus].priority -= 1
                logging.detail("Task %s: Priority Decrement to: %s", focus, self.tasks[focus].priority)
            case TaskArtifact() as focus:
                focus.priority -= 1

        return focus

    def queue_entry(self, name:str|Ident|Concrete[TaskSpec]|Task_p, *, from_user:bool=False, status:TaskStatus_e|ArtifactStatus_e=None) -> None|Concrete[Ident]:
        """
          Queue a task by name|spec|Task_p.
          registers and instantiates the relevant spec, inserts it into the network
          Does *not* rebuild the network

          returns a task name if the network has changed, else None.

          kwarg 'from_user' signifies the enty is a starting target, adding cli args if necessary and linking to the root.
        """

        prepped_name : None|TaskName|TaskArtifact = None
        # Prep the task: register and instantiate
        match name:
            case TaskSpec() as spec:
                self.register_spec(spec)
                return self.queue_entry(spec.name, from_user=from_user, status=status)
            case Task_p() as task if task.name not in self.tasks:
                self.register_spec(task.spec)
                instance = self._instantiate_spec(task.name, add_cli=from_user)
                # update the task with its concrete spec
                task.spec = self.specs[instance]
                self.connect(instance, None if from_user else False)
                prepped_name = self._make_task(instance, task_obj=task)
            case TaskArtifact() if name in self.network.nodes:
                prepped_name = name
            case TaskName() if name == self._root_node:
                prepped_name = None
            case TaskName() if name in self.active_set:
                prepped_name = name
            case TaskName() if name in self.tasks:
                prepped_name  = self.tasks[name].name
            case TaskName() if name in self.network:
                prepped_name = name
            case TaskName() if not from_user and (instance:=self._maybe_reuse_instantiation(name)) is not None:
                prepped_name = instance
                self.connect(instance, None if from_user else False)
            case TaskName() if name in self.specs:
                assert(not TaskName(name).is_uniq()), name
                instance : TaskName = self._instantiate_spec(name, add_cli=from_user)
                self.connect(instance, None if from_user else False)
                prepped_name = instance
            case TaskName():
                raise doot.errors.TrackingError("Unrecognized queue argument provided, it may not be registered", name)
            case str():
                return self.queue_entry(TaskName(name), from_user=from_user)
            case _:
                raise doot.errors.TrackingError("Unrecognized queue argument provided, it may not be registered", name)

        ## --
        if prepped_name is None:
            return None
        assert(prepped_name in self.network)

        final_name      : None|TaskName|TaskArtifact = None
        target_priority : int                        = self._declare_priority
        match prepped_name:
            case TaskName() if TaskName.bmark_e.head in prepped_name:
                assert(prepped_name.is_uniq())
                assert(prepped_name in self.specs)
                final_name      = self._make_task(prepped_name)
                target_priority = self.tasks[final_name].priority
            case TaskName() if TaskName.bmark_e.extend in prepped_name:
                assert(prepped_name.is_uniq())
                assert(prepped_name in self.specs)
                final_name      = self._make_task(prepped_name)
                target_priority = self.tasks[final_name].priority
            case TaskName():
                assert(prepped_name.is_uniq())
                assert(prepped_name in self.specs)
                final_name      = self._make_task(prepped_name)
                target_priority = self.tasks[final_name].priority
            case TaskArtifact():
                assert(prepped_name in self.artifacts)
                final_name = prepped_name
                target_priority = prepped_name.priority

        self.active_set.add(final_name)
        self._queue.add(final_name, priority=target_priority)
        # Apply the override status if necessary:
        match status:
            case TaskStatus_e() | ArtifactStatus_e():
                self.set_status(final_name, status)
            case None:
                status = self.get_status(final_name)
        logging.detail("Queued Entry at priority: %s, status: %s: %s", target_priority, status, final_name)
        return final_name

    def clear_queue(self) -> None:
        """ Remove everything from the task queue,

        """
        # TODO _queue the task's failure/cleanup tasks
        self.active_set =  set()
        self.task_queue = boltons.queueutils.HeapPriorityQueue()

##--|
@Proto(TaskTracker_p, check=False)
@Mixin(_TrackerStore, _TrackerNetwork, _TrackerQueue_boltons, allow_inheritance=True)
class BaseTracker:
    """ The public part of the standard tracker implementation """
    pass
