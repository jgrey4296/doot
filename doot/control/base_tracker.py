#!/usr/bin/env python3
"""
Abstract Specs: A[n]
Concrete Specs: C[n]
Task:           T[n]

  Expansion: ∀x ∈ C[n].depends_on => A[x] -> C[x]
  Head: C[1].depends_on[A[n].$head$] => A[n] -> C[n], A[n].head -> C[n].head, connect

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
                    Generic, Iterable, Iterator, Mapping, Self,
                    MutableMapping, Protocol, Sequence, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import boltons.queueutils
import more_itertools as mitz
import networkx as nx
import tomlguard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import FailPolicy_p, Job_i, Task_i, TaskRunner_i, TaskTracker_i
from doot._structs.relation_spec import RelationSpec
from doot.enums import TaskMeta_f, QueueMeta_e, TaskStatus_e, LocationMeta_f, RelationMeta_e, EdgeType_e
from doot.structs import (ActionSpec, CodeReference, TaskArtifact,
                          TaskName, TaskSpec)
from doot.task.base_task import DootTask

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

ROOT                           : Final[str]                  = "root::_" # Root node of dependency graph
EXPANDED                       : Final[str]                  = "expanded"  # Node attribute name
REACTIVE_ADD                   : Final[str]                  = "reactive-add"
ARTIFACT_EDGES                 : Final[set[EdgeType_e]]      = EdgeType_e.artifact_edge_set
DECLARE_PRIORITY               : Final[int]                  = 10
MIN_PRIORITY                   : Final[int]                  = -10
INITAL_SOURCE_CHAIN_COUNT      : Final[int]                  = 10

AbstractId                     : TypeAlias                   = TaskName|TaskArtifact
ConcreteId                     : TypeAlias                   = TaskName|TaskArtifact
AnyId                          : TypeAlias                   = TaskName|TaskArtifact
AbstractSpec                   : TypeAlias                   = TaskSpec
ConcreteSpec                   : TypeAlias                   = TaskSpec
AnySpec                        : TypeAlias                   = TaskSpec

ActionElem                     : TypeAlias                   = ActionSpec|RelationSpec
ActionGroup                    : TypeAlias                   = list[ActionElem]

class _TrackerStore:
    """ Stores and manipulates specs, tasks, and artifacts """

    def __init__(self):
        super().__init__()
        # All [Abstract, Concrete] Specs:
        self.specs                : dict[AnyId, AnySpec]                          = {}
        # Mapping (Abstract Spec) -> Concrete Specs. Every id, abstract and concerete, has a spec in specs.
        # TODO: Check first entry is always uncustomised
        self.concrete             : dict[AbstractId, list[ConcreteId]]            = defaultdict(lambda: [])
        # Mapping Artifact -> list[Spec] of solo transformer specs. Every abstractId has a spec in specs.
        self._transformer_specs   : dict[TaskArtifact, list[AbstractId]]      = defaultdict(lambda: [])
        # All (Concrete Specs) Task objects. Invariant: every key in tasks has a matching key in specs.
        self.tasks                : dict[ConcreteId, Task_i]                      = {}
        # Artifact -> list[TaskName] of related tasks
        self.artifacts            : dict[TaskArtifact, list[AbstractId]]      = defaultdict(set)
        self._artifact_status     : dict[TaskArtifact, TaskStatus_e]          = defaultdict(lambda: TaskStatus_e.ARTIFACT)
        # Artifact sets
        self._abstract_artifacts  : set[TaskArtifact]                         = set()
        self._concrete_artifacts  : set[TaskArtifact]                         = set()
        # requirements.
        self._requirements        : dict[ConcreteId, list[RelationSpec]]          = defaultdict(lambda: [])

    def _maybe_reuse_instantiation(self, name:TaskName, *, add_cli:bool=False, extra:bool=False) -> None|ConcreteId:
        """ if an existing concrete spec exists, use it if it has no conflicts """
        if TaskMeta_f.CONCRETE in name:
            logging.debug("Not reusing instantiation because name is concrete: %s", name)
            return None
        if name not in self.specs:
            logging.debug("Not reusing instantiation because name doesn't have a matching spec: %s", name)
            return None
        if extra or add_cli:
            logging.debug("Not reusing instantiation because extra or cli args were requested: %s", name)
            return None

        if not bool(self.concrete[name]):
            logging.debug("Not reusing instantiation because there is no instantiation to reuse: %s", name)
            return None

        existing_abstract = self.specs[name]
        match [x for x in self.concrete[name] if self.specs[x].match_with_constraints(existing_abstract)]:
            case []:
                logging.debug("Not reusing instantiation because existing specs dont match with constraints: %s", name)
                return None
            case [x, *xs]:
                logging.debug("Reusing Concrete Spec: %s for %s", x, name)
                # Can use an existing concrete spec
                return x


    def _get_task_source_chain(self, name:AbstractId) -> list[AbstractSpec]:
        """ get the chain of sources for a task.
          this traces from an instance back towards the root,
          returning [root, ... grandparent, parent, instance].

          traces with the *last* value in spec.sources.
        """
        assert(TaskMeta_f.CONCRETE not in name)
        spec                          = self.specs[name]
        chain   : list[TaskSpec]  = []
        current : None|TaskSpec   = spec
        count   : int = INITAL_SOURCE_CHAIN_COUNT
        while current is not None:
            if 0 > count:
                raise doot.errors.DootTaskTrackingError("Building a source chain grew to large", name)
            count -= 1
            match current: # Determine the base
                case TaskSpec(name=name) if TaskMeta_f.JOB_HEAD in name:
                    # job heads are generated, so don't have a source chain
                    chain.append(current)
                    current = None
                case TaskSpec(sources=[pl.Path()]|[]):
                    chain.append(current)
                    current = None
                case TaskSpec(sources=[*xs, TaskName() as src]):
                    chain.append(current)
                    current = self.specs.get(src, None)
                case TaskSpec(sources=[*xs, None]):
                    # Stop the chain search
                    chain.append(current)
                    current = None
                case _:
                    raise doot.errors.DootTaskTrackingError("Unknown spec customization attempt", spec, current, chain)

        chain.reverse()
        return chain

    def _instantiate_spec(self, name:AbstractId, *, add_cli:bool=False, extra:None|dict|tomlguard.TomlGuard=None) -> ConcreteId:
        """ Convert an Asbtract Spec into a Concrete Spec,
          Reuses a existing concrete spec if possible.
          """
        match self._maybe_reuse_instantiation(name, add_cli=add_cli, extra=bool(extra)):
            case None:
                logging.debug("Could not reuse an instantiation of: %s", name)
                pass
            case TaskName() as existing:
                logging.debug("Reusing instantiation: %s for %s", existing, name)
                return existing

        spec = self.specs[name]
        # Instantiate the spec from its source chain
        match self._get_task_source_chain(name):
            case []:
                raise doot.errors.DootTaskTrackingError("this shouldn't be possible", name)
            case [x]:
                # No chain, just instantiate the spec
                instance_spec = x.instantiate_onto(None)
            case [*xs]:
                # (reversed because the chain goes from spec -> ancestor)
                # and you want to instantiate descendents onto ancestors
                instance_spec = ftz.reduce(lambda x, y: y.instantiate_onto(x), xs)

        logging.debug("Instantiating: %s into %s", name, instance_spec.name)
        assert(instance_spec is not None)
        if add_cli:
            # only add cli args explicitly. ie: when the task has been queued by the user
            instance_spec = self._insert_cli_args_into_spec(instance_spec)

        if extra:
            # apply additional settings onto the instance
            instance_spec = instance_spec.specialize_from(extra)

        assert(TaskMeta_f.CONCRETE in instance_spec.flags)
        # Map abstract -> concrete
        self.concrete[name].append(instance_spec.name)
        # register the actual concrete spec
        self.register_spec(instance_spec)

        assert(instance_spec.name in self.specs)
        return instance_spec.name

    def _instantiate_relation(self, dep:RelationSpec, *, control:ConcreteId) -> ConcreteId:
        """ find a matching dependency/requirement according to a set of keys in the spec, or create a matching instance
          if theres no constraints, will just instantiate.
          """
        control_spec              = self.specs[control]
        successful_matches        = []
        match self.concrete.get(dep.target, None):
            case [] | None if dep.target not in self.specs:
                raise doot.errors.DootTaskTrackingError("Unknown target declared in Constrained Relation", control, dep.target)
            case [] | None:
                pass
            case [*xs] if not bool(dep.constraints) and not bool(dep.injections):
                successful_matches = [x for x in xs if x != control]
            case [*xs]:
                # concrete instances exist, match on them
                potentials : list[TaskSpec] = [self.specs[x] for x in xs if x != control]
                successful_matches += [x.name for x in potentials if x.match_with_constraints(control_spec, relation=dep)]


        match successful_matches:
            case []: # No matches, instantiate
                extra    : None|dict     = control_spec.build_injection(dep)
                instance : TaskName = self._instantiate_spec(dep.target, extra=extra)
                if not self.specs[instance].match_with_constraints(control_spec, relation=dep):
                    raise doot.errors.DootTaskTrackingError("Could not instantiate a spec that passes constraints", dep, control)
                return instance
            case [x]: # One match, connect it
                assert(x in self.specs)
                assert(TaskMeta_f.CONCRETE in x)
                instance : TaskName = x
                return instance
            case [*xs, x]: # TODO check this.
                # Use most recent instance?
                assert(x in self.specs)
                assert(TaskMeta_f.CONCRETE in x)
                instance : TaskName = x
                return instance

    def _instantiate_transformer(self, name:AbstractId, artifact:TaskArtifact) -> None|ConcreteId:
        spec = self.specs[name]
        match spec.instantiate_transformer(artifact):
            case None:
                return None
            case TaskSpec() as instance:
                assert(TaskMeta_f.CONCRETE | TaskMeta_f.TRANSFORMER in instance.flags)
                assert(TaskMeta_f.CONCRETE | TaskMeta_f.TRANSFORMER in instance.name)
                self.concrete[name].append(instance.name)
                self.register_spec(instance)
                return instance.name

    def _insert_cli_args_into_spec(self, spec:ConcreteSpec) -> ConcreteSpec:
        """ Takes a task spec, and inserts matching cli args into it if necessary """
        logging.debug("Applying CLI Args to: %s", spec.name)
        spec_extra : dict = dict(spec.extra.items() or [])
        if 'cli' in spec_extra:
            del spec_extra['cli']

        # Apply any cli defined args
        for cli in spec.extra.on_fail([]).cli():
            if cli.name not in spec_extra:
                spec_extra[cli.name] = cli.default

        source = str(spec.name.root())
        for key,val in doot.args.on_fail({}).tasks[source]().items():
            spec_extra[key] = val

        cli_spec = spec.specialize_from(spec_extra)
        return cli_spec

    def _make_task(self, name:ConcreteId, *, task_obj:Task_i=None) -> ConcreteId:
        """ Build a Concrete Spec's Task object
          if a task_obj is provided, store that instead

          return the name of the task
          """
        if not isinstance(name, TaskName):
            raise doot.errors.DootTaskTrackingError("Tried to add a not-task", name)
        if TaskMeta_f.CONCRETE not in name:
            raise doot.errors.DootTaskTrackingError("Tried to add a task using a non-concrete spec", name)
        if name not in self.network.nodes:
            raise doot.errors.DootTaskTrackingError("Tried to add a non-network task ", name)
        if name in self.tasks:
            return name

        logging.debug("Constructing Task Object: %s", name)
        match task_obj:
            case None:
                spec = self.specs[name]
                task : Task_i = spec.make()
            case Task_i():
                task = task_obj
            case _:
                raise doot.errors.DootTaskTrackingError("Supplied task object isn't a task_i", task_obj)

        # Store it
        self.tasks[name] = task
        return name

    def _register_artifacts(self, name:ConcreteSpec) -> None:
        """ Register the artifacts in a spec """
        if name not in self.specs:
            raise doot.errors.DootTaskTrackingError("tried to register artifacts of a non-registered spec", name)

        spec = self.specs[name]

        match spec.transformer_of():
            case None:
                pass
            case (pre, post):
                logging.debug("Registering Transformer: %s : %s -> %s", spec.name.readable, pre, post)
                self._transformer_specs[pre.target].append(spec.name)
                self._transformer_specs[post.target].append(spec.name)

        if TaskMeta_f.CONCRETE in spec.flags:
            return

        for rel in spec.depends_on + spec.required_for:
            match rel:
                case RelationSpec(target=TaskArtifact() as art):
                    logging.debug("Registering Artifact Relation: %s, %s", art, spec.name)
                    # Link artifact to its source task
                    self.artifacts[art].add(spec.name)
                    # Add it to the relevant abstract/concrete set
                    if LocationMeta_f.abstract in art:
                        self._abstract_artifacts.add(art)
                    else:
                        self._concrete_artifacts.add(art)
                case _:
                    pass

    def register_spec(self, *specs:AnySpec) -> None:
        """ Register task specs, abstract or concrete.
        An initial concrete instance will be created for any abstract spec.
        """
        for spec in specs:
            if spec.name in self.specs:
                continue
            if TaskMeta_f.DISABLED in spec.flags:
                logging.debug("Ignoring Registration of disabled task: %s", spec.name.readable)
                continue

            self.specs[spec.name] = spec
            logging.debug("Registered Spec: %s", spec.name)

            # Register the head and cleanup specs:
            self.register_spec(*spec.job_top())
            self._register_artifacts(spec.name)
            # Register Requirements:
            for rel in spec.required_for:
                match rel:
                    case RelationSpec(target=target, relation=RelationMeta_e.req) if TaskMeta_f.CONCRETE not in spec.name:
                        logging.debug("Registering Requirement: %s : %s", target, rel.invert(spec.name))
                        self._requirements[target].append(rel.invert(spec.name))
                    case _: # Ignore action specs
                        pass

            # If the spec is abstract, create an initial concrete version
            if not bool(spec.flags & (TaskMeta_f.TRANSFORMER|TaskMeta_f.CONCRETE)):
                logging.debug("Instantiating Initial Concrete for abstract: %s", spec.name)
                self._instantiate_spec(spec.name)

    def get_status(self, task:ConcreteId) -> TaskStatus_e:
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

    def set_status(self, task:ConcreteId|Task_i, status:TaskStatus_e) -> bool:
        """ update the state of a task in the dependency graph
          Returns True on status update,
          False on no task or artifact to update.
        """
        logging.debug("Updating State: %s -> %s", task, status)
        match task, status:
            case TaskName(), _ if task == self._root_node:
                return False
            case Task_i(), TaskStatus_e() if task.name in self.tasks:
                self.tasks[task.name].status = status
            case TaskArtifact(), TaskStatus_e():
                self._artifact_status[task] = status
            case TaskName(), TaskStatus_e() if task in self.tasks:
                self.tasks[task].status = status
            case TaskName(), TaskStatus_e():
                logging.debug("Not Setting Status of %s, its hasn't been started", task)
                return False
            case _, _:
                raise doot.errors.DootTaskTrackingError("Bad task update status args", task, status)

        return True

class _TrackerNetwork:
    """ the network of concrete tasks and their dependencies """

    def __init__(self):
        super().__init__()
        self._root_node        : TaskName                              = TaskName.build(ROOT)
        self._declare_priority : int                                       = DECLARE_PRIORITY
        self._min_priority     : int                                       = MIN_PRIORITY
        self.network           : nx.DiGraph[ConcreteId] = nx.DiGraph()
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
        def abstraction_test(x):
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

    def _expand_task_node(self, name:TaskName) -> set[ConcreteId]:
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
        root      = spec.name.root()
        head_name = root.job_head()
        match [x for x in self.network.succ[spec.name] if head_name < x]:
            case []: # No head yet, add it
                conc_head = self.concrete[head_name][0]
                self.connect(spec.name, conc_head)
                return [conc_head]
            case [*xs, x]: # Use the most recent head
                return [x]

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

class _TrackerQueue_boltons:
    """ The _queue of tasks """

    def __init__(self):
        super().__init__()
        self.active_set         : list[ConcreteId]                     = set()
        self.execution_trace    : list[ConcreteId]                     = []
        self._queue             : boltons.queueutils.HeapPriorityQueue      = boltons.queueutils.HeapPriorityQueue()

    def __bool__(self):
        return self._queue.peek(default=None) is not None

    def _maybe_implicit_queue(self, task:Task_i) -> None:
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
                raise doot.errors.DootTaskTrackingError("Unknown _queue behaviour specified: %s", task.spec.queue_behaviour)

    def _reactive_queue(self, focus:ConcreteId) -> None:
        """ Queue any known task in the network that auto-reacts to a focus """
        for adj in self.network.adj[focus]:
            if self.network.nodes[adj].get(REACTIVE_ADD, False):
                self.queue_entry(adj, silent=True)

    def _reactive_fail_queue(self, focus:ConcreteId) -> None:
        """ TODO: make reactive failure tasks that can be triggered from
          a tasks 'on_fail' collection
          """
        raise NotImplementedError()

    def deque_entry(self, *, peek:bool=False) -> ConcreteId:
        """ remove (or peek) the top task from the _queue .
          decrements the priority when popped.
        """
        if peek:
            return self._queue.peek()

        match self._queue.pop():
            case TaskName() as focus if self.tasks[focus].priority < self._min_priority:
                logging.warning("Task halted due to reaching minimum priority while tracking: %s", focus)
                self.set_status(focus, TaskStatus_e.HALTED)
            case TaskName() as focus:
                self.tasks[focus].priority -= 1
                logging.debug("Task %s: Priority Decrement to: %s", focus, self.tasks[focus].priority)
            case TaskArtifact() as focus:
                focus.priority -= 1

        return focus

    def queue_entry(self, name:str|AnyId|ConcreteSpec|Task_i, *, from_user:bool=False, status:TaskStatus_e=None) -> None|ConcreteId:
        """
          Queue a task by name|spec|Task_i.
          registers and instantiates the relevant spec, inserts it into the network
          Does *not* rebuild the network

          returns a task name if the network has changed, else None.

          kwarg 'from_user' signifies the enty is a starting target, adding cli args if necessary and linking to the root.
        """

        prepped_name : None|TaskName|TaskArtifact = None
        # Prep the task: register and instantiate
        match name:
            case str():
                return self.queue_entry(TaskName.build(name), from_user=from_user)
            case TaskSpec() as spec:
                self.register_spec(spec)
                return self.queue_entry(spec.name, from_user=from_user, status=status)
            case Task_i() as task if task.name not in self.tasks:
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
                assert(TaskMeta_f.CONCRETE not in TaskName.build(name))
                instance : TaskName = self._instantiate_spec(name, add_cli=from_user)
                self.connect(instance, None if from_user else False)
                prepped_name = instance
            case _:
                raise doot.errors.DootTaskTrackingError("Unrecognized queue argument provided, it may not be registered", name)

        ## --
        if prepped_name is None:
            return None
        assert(prepped_name in self.network)

        final_name      : None|TaskName|TaskArtifact = None
        target_priority : int                        = self._declare_priority
        match prepped_name:
            case TaskName() if TaskMeta_f.JOB_HEAD in prepped_name:
                assert(TaskMeta_f.CONCRETE in prepped_name)
                assert(prepped_name in self.specs)
                final_name      = self._make_task(prepped_name)
                target_priority = self.tasks[final_name].priority
            case TaskName() if TaskMeta_f.JOB in prepped_name:
                assert(TaskMeta_f.CONCRETE in prepped_name)
                assert(prepped_name in self.specs)
                final_name      = self._make_task(prepped_name)
                target_priority = self.tasks[final_name].priority
            case TaskName():
                assert(TaskMeta_f.CONCRETE in prepped_name)
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
            case TaskStatus_e():
                self.set_status(final_name, status)
            case None:
                status = self.get_status(final_name)
        logging.debug("Queued Entry at priority: %s, status: %s: %s", target_priority, status, final_name)
        return final_name

    def clear_queue(self) -> None:
        """ Remove everything from the task queue,

        """
        # TODO _queue the task's failure/cleanup tasks
        self.active_set =  set()
        self.task_queue = boltons.queueutils.HeapPriorityQueue()

class BaseTracker(_TrackerStore, _TrackerNetwork, _TrackerQueue_boltons, TaskTracker_i):
    """ The public part of the standard tracker implementation """
    pass
