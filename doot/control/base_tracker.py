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
from doot.enums import TaskFlags, TaskQueueMeta, TaskStatus_e, LocationMeta
from doot.structs import (DootActionSpec, DootCodeReference, DootTaskArtifact,
                          DootTaskName, DootTaskSpec)
from doot.task.base_task import DootTask

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

class EDGE_E(enum.Enum):
    """ Enum describing the possible edges of the task tracker's task network """
    TASK               = enum.auto()
    ARTIFACT           = enum.auto()
    TASK_CROSS         = enum.auto() # Task to artifact
    ARTIFACT_CROSS     = enum.auto() # artifact to task

ROOT                  : Final[str]                  = "root::_" # Root node of dependency graph
EXPANDED              : Final[str]                  = "expanded"  # Node attribute name
REACTIVE_ADD          : Final[str]                  = "reactive-add"
ARTIFACT_EDGES        : Final[set[EDGE_E]]          = [EDGE_E.ARTIFACT, EDGE_E.TASK_CROSS]
DECLARE_PRIORITY      : Final[int]                  = 10
MIN_PRIORITY          : Final[int]                  = -10

ActionElem            : TypeAlias                   = DootTaskName|DootTaskArtifact|DootActionSpec|RelationSpec
ActionGroup           : TypeAlias                   = list[ActionElem]

class _TrackerStore:
    """ Stores and manipulates specs, tasks, and artifacts """

    def __init__(self):
        super().__init__()
        # All [Abstract, Concrete] Specs:
        self.specs           : dict[DootTaskName, DootTaskSpec]          = {}
        # Mapping (Abstract Spec) -> Concrete Specs. first entry is always uncustomised
        self.concrete       : dict[DootTaskName, list[DootTaskName]]     = defaultdict(lambda: [])
        # All (Concrete Specs) Task objects. key is always in both self.specs, and self.concrete's values
        self.tasks           : dict[DootTaskName, Task_i]                = {}
        # Artifact -> list[TaskName]
        self.artifacts            : dict[DootTaskArtifact, list[DootTaskName]] = defaultdict(lambda: [])
        # Artifact sets
        self._abstract_artifacts  : set[DootTaskArtifact] = set()
        self._concrete_artifacts  : set[DootTaskArtifact] = set()

    def _instantiate_spec(self, name:DootTaskName, *, add_cli:bool=False, extra:None|dict|tomlguard.TomlGuard=None) -> DootTaskName:
        """ Convert an Asbtract Spec into a Concrete Spec,
          Reuses a existing concrete spec if possible.
          """
        assert(TaskFlags.CONCRETE not in name)
        spec = self.specs[name]

        needs_minimal_customisation = True
        needs_minimal_customisation &= not bool(extra)
        needs_minimal_customisation &= not add_cli
        needs_minimal_customisation &= name in self.concrete[name]
        if needs_minimal_customisation:
            match [x for x in self.concrete[name] if self.spec[x].match_with_constriants(spec)]:
                case []:
                    pass
                case [x, *xs]:
                    # Can use an existing concrete spec
                    return x

        # Else you've got to customize it
        # So get its source chain
        chain : list[DootTaskSpec] = []
        current                    = spec
        while current is not None:
            match current: # Determine the base
                case DootTaskSpec(source=pl.Path()|None):
                    chain.append(current)
                    current = None
                case DootTaskSpec(source=DootTaskName() as src):
                    chain.append(current)
                    current = self.specs.get(src, None)
                case _:
                    raise doot.errors.DootTaskTrackingError("Unknown spec customization attempt", spec)

        # Reverse the chain a instantiate it
        match chain:
            case []:
                raise doot.errors.DootTaskTrackingError("this shouldn't be possible", spec)
            case [x]:
                custom_spec = x.instantiate_onto(None)
            case [*xs]:
                custom_spec = ftz.reduce(lambda x, y: y.instantiate_onto(x), reversed(xs[:-1]), xs[-1])

        assert(custom_spec is not None)
        if add_cli:
            custom_spec = self._insert_cli_args_into_spec(custom_spec)

        if extra:
            custom_spec = custom_spec.specialize_from(extra)

        custom_spec.flags |= TaskFlags.CONCRETE
        # Map abstract -> concrete
        self.concrete[name].append(custom_spec.name)
        # register the actual concrete
        self.register_spec(custom_spec)

        logging.debug("Instantiated: %s", custom_spec.name)
        return custom_spec.name

    def _instantiate_respecting_constraints(self, dep:RelationSpec, *, control:DootTaskName) -> DootTaskName:
        """ find a matching dependency/requirement according to a set of keys in the spec, or create a matching instance """
        target                    = self.specs.get(dep.target, None)
        control_spec              = self.specs[control]
        successful_matches        = []
        match self.concrete[dep.target]:
            case [] if dep.target not in self.specs:
                raise doot.errors.DootTaskTrackingError("Unknown target declared in Constrained Relation", name, dep.target)
            case []:
                pass
            case [*xs] if not bool(dep.constraints):
                successful_matches = xs
            case [*xs]:
                # concrete instances exist, match on them
                potentials = [self.specs[x] for x in xs]
                successful_matches += [x.name for x in potentials if x.match_with_constraints(control_spec, relation=dep)]

        match successful_matches:
            case []: # No matches, instantiate
                extra    : dict                   = control_spec.build_relevant_data(dep)
                instance : DootTaskName           = self._instantiate_spec(dep.target, extra=extra)
                return instance
            case [x]: # One match, connect it
                instance : DootTaskName = x
                return instance
            case [*xs]:
                raise doot.errors.DootTaskTrackingError("multiple matches occured, this shouldn't be possible", dep, control, xs)

    def _insert_cli_args_into_spec(self, spec:DootTaskSpec) -> DootTaskSpec:
        """ Takes a task spec, and inserts matching cli args into it if necessary """
        spec_extra : dict = dict(spec.extra.items() or [])

        for cli in spec.extra.on_fail([]).cli():
            if cli.name not in spec_extra:
                spec_extra[cli.name] = cli.default

        match spec.source:
            case None:
                source = spec.name
            case pl.Path():
                source = spec.name
            case DootTaskName():
                source = spec.source

        if source not in doot.args.on_fail({}).tasks():
            return spec.specialize_from(spec_extra)

        for key,val in doot.args.tasks[source].items():
            spec_extra[key] = val

        cli_spec = spec.specialize_from(spec_extra)
        return cli_spec

    def _assert_specs_exists(self, sources:ActionGroup) -> None:
        """ Ensure that for all given sources, a spec or artifact is registered
        raises a doot.errors.DootTaskTrackingError if any are missing
        """
        missing = []
        for name in sources:
            match name:
                case DootTaskName() if name.job_head() == name and name.root() in self.specs:
                    pass
                case DootTaskName() if name not in self.specs:
                    missing.append(name)
                case DootTaskName():
                    pass
                case DootTaskArtifact() if name not in self.artifacts:
                    missing.append(name)
                case DootTaskArtifact():
                    pass
                case DootActionSpec():
                    pass

        if bool(missing):
            raise doot.errors.DootTaskTrackingError("Resources were missing", missing)

    def _make_task(self, name:DootTaskName) -> DootTaskName:
        """ Build a Concrete Spec's Task object """
        if not isinstance(name, DootTaskName):
            raise doot.errors.DootTaskTrackingError("Tried to add a not-task", name)
        if TaskFlags.CONCRETE not in self.specs[name].flags:
            raise doot.errors.DootTaskTrackingError("Tried to add a task using a non-concrete spec", name)
        if name in self.tasks:
            return name

        spec = self.specs[name]
        task : Task_i = spec.make()

        # Store it
        self.tasks[task.fullname] = task
        return task.fullname

    def register_spec(self, spec:DootTaskSpec) -> None:
        """ Register a spec, abstract or concrete """
        if spec.name in self.specs:
            return
        if TaskFlags.DISABLED in spec.flags:
            logging.debug("Ignoring Registration of disabled task: %s", spec.name)
            return

        self.specs[spec.name] = spec
        self.register_artifacts(spec.name)
        logging.debug("Registered Spec: %s", spec.name)
        match spec.job_top():
            case None:
                pass
            case DootTaskSpec() as head:
                self.specs[head.name] = head
                logging.debug("Registered Head Spec: %s", head.name)

    def register_artifacts(self, name:DootTaskName) -> None:
        """ Register the artifacts in a spec """
        if name not in self.specs:
            raise doot.errors.DootTaskTrackingError("tried to register artifacts of a non-registered spec", name)

        spec = self.specs[name]
        for rel in spec.depends_on + spec.required_for:
            match rel:
                case RelationSpec(target=DootTaskArtifact() as art) if art in self.artifacts:
                    # Already Registered
                    pass
                case RelationSpec(target=DootTaskArtifact() as art):
                    # Link artifact to its source task
                    self.artifacts[art].append(spec.name)
                    # Add it to the relevant abstract/concrete set
                    if LocationMeta.abstract in art:
                        self._abstract_artifacts.add(art)
                    else:
                        self._concrete_artifacts.add(art)
                case _:
                    pass

    def task_status(self, task:DootTaskName|DootTaskArtifact) -> TaskStatus_e:
        """ Get the status of a task """
        match task:
            case DootTaskName() if task in self.tasks:
                return self.tasks[task].status
            case DootTaskArtifact() if task.exists:
                return TaskStatus_e.EXISTS
            case DootTaskArtifact():
                return TaskStatus_e.ARTIFACT
            case _:
                raise doot.errors.DootTaskTrackingError("Unknown Task state requested: %s", task)

    def update_status(self, task:str|Task_i|DootTaskArtifact, status:TaskStatus_e) -> None:
        """ update the state of a task in the dependency graph """
        logging.debug("Updating State: %s -> %s", task, status)
        match task, status:
            case DootTaskArtifact(), _:
                raise NotImplementedError()
            case str(), TaskStatus_e():
                # convert str to task name
                raise NotImplementedError()
            case DootTaskName(), TaskStatus_e() if task in self.tasks:
                self.tasks[task].status = status
            case Task_i(), TaskStatus_e() if task.fullname in self.tasks:
                self.tasks[task.fullname].status = status
            case _, _:
                raise doot.errors.DootTaskTrackingError("Bad task update status args", task, status)

    def registered_set(self) -> set[DootTaskName]:
        """ Get the set of tasks which have been declared, directly or indirectly """
        return set(self.specs.keys())

    def instance_set(self) -> set[DootTaskName]:
        """ get the set of task spec names which have been concrete"""
        return set(self.concrete.keys())

    def task_set(self) -> set[DootTaskName]:
        """ get the set of names of running tasks """
        return set(self.tasks.keys())

    def artifact_set(self) -> set[DootTaskArtifact]:
        return set(self.artifacts)

class _TrackerNetwork:
    """ the network of tasks and their dependencies """

    def __init__(self):
        super().__init__()
        self._root_node        : DootTaskName                              = DootTaskName.build(ROOT)
        self._declare_priority : int                                       = DECLARE_PRIORITY
        self._min_priority     : int                                       = MIN_PRIORITY
        self.network           : nx.DiGraph[DootTaskName|DootTaskArtifact] = nx.DiGraph()

        self._add_node(self._root_node)

    def _add_node(self, name:DootTaskName|DootTaskArtifact) -> None:
        """idempotent"""
        match name:
            case x if x is self._root_node:
                self.network.add_node(name)
                self.network.nodes[name][EXPANDED]     = True
                self.network.nodes[name][REACTIVE_ADD] = False
                self._root_node.meta                  |= TaskFlags.CONCRETE
            case DootTaskName() if TaskFlags.CONCRETE not in name:
                raise ValueError("Nodes should only be instantiated spec names")
            case _ if name in self.network.nodes:
                return
            case _:
                # Add node with metadata
                self.network.add_node(name)
                self.network.nodes[name][EXPANDED]     = False
                self.network.nodes[name][REACTIVE_ADD] = False

    def _expand_task_node(self, name:DootTaskName) -> set[DootTaskName|DootTaskArtifact]:
        """ expand a task node, instantiating and connecting to its dependencies and dependents,
        *without* expanding those new nodes.
        returns a list of the new nodes tasknames
        """
        assert(TaskFlags.CONCRETE in name)
        assert(not self.network.nodes[name].get(EXPANDED, False))
        spec       = self.specs[name]
        spec_pred, spec_succ = self.network.pred[name], self.network.succ[name]
        deps, reqs = spec.depends_on, spec.required_for
        # TODO possibly filter deps and reqs by existing pred and succs that are abstract < concrete
        self._assert_specs_exists(deps + reqs)
        to_expand  = set()
        logging.debug("Expanding: %s : Pre(%s), Post(%s)", name, [str(x) for x in deps], [str(x) for x in reqs])
        for rel, is_dep_p in chain(zip(deps, cycle([True])), zip(reqs, cycle([False]))):
            relevant_edges = spec_pred if is_dep_p else spec_succ
            match rel:
                case DootActionSpec():
                    # Action specs are no-ops in the tracker
                    continue
                case RelationSpec(target=DootTaskName() as target) if rel.match_simple_edge(relevant_edges.keys()):
                    # already linked, ignore.
                    continue
                case RelationSpec(target=DootTaskArtifact() as target):
                    # An artifact relation
                    self.connect(*rel.to_edge(name))
                    to_expand.add(target)
                case RelationSpec(target=DootTaskName(), constraints=list()):
                    # Get specs and instances with matching target
                    instance = self._instantiate_respecting_constraints(rel, control=name)
                    self.connect(*rel.to_edge(name, instance=instance))
                    to_expand.add(instance)
                    continue
                case RelationSpec(target=DootTaskName() as target):
                    assert(TaskFlags.CONCRETE not in target)
                    assert(rel.constraints is None)
                    instance : DootTaskName = self._instantiate_spec(target)
                    self.connect(*rel.to_edge(name, instance=instance))
                    to_expand.add(instance)
                case RelationSpec(target=DootTaskName() as target):
                    # already in network, connected, expanded: pass
                    pass
                case _:
                    raise doot.errors.DootTaskTrackingError("Unknown dependency or requirement", spec, d)
        else:
            assert(name in self.network.nodes)
            self.network.nodes[name][EXPANDED] = True
        return to_expand

    def _expand_artifact(self, artifact:DootTaskArtifact) -> set[DootTaskName|DootTaskArtifact]:
        assert(artifact in self.artifacts)
        assert(not self.network.nodes[artifact].get(EXPANDED, False))
        logging.debug("Expanding Artifact: %s", artifact)
        to_expand = set()

        for name in [x for x in self.artifacts[artifact]]:
            if TaskFlags.CONCRETE in name:
                instance = name
                self.connect(instance, False)
                to_expand.add(instance)
            elif bool(self.concrete[name]):
                for instance in self.concrete[name]:
                    self.connect(instance, False)
                    to_expand.add(instance)
            else:
                instance = self._instantiate_spec(name)
                self.connect(instance, False)
                to_expand.add(instance)

        match artifact.is_concrete:
            case True:
                # connect to any matching abstract artifacts
                for abs in [x for x in self._abstract_artifacts if artifact in x]:
                    self.connect(artifact, abs)
                    to_expand.add(abs)
            case False:
                # connect to any matching concrete artifacts
                for conc in [x for x in self._concrete_artifacts if x in artifact]:
                    self.connect(conc, artifact)
                    to_expand.add(conc)
                pass

        return to_expand

    def _fixup_artifacts(self) -> None:
        """
        connect matching concrete and abstract artifacts in the network
        """
        if not bool(self.artifacts):
            return

        # raise NotImplementedError()

    def concrete_edges(self, name:DootTaskName|DootTaskArtifact) -> tomlguard.TomlGuard:
        """ get the concrete edges of a task.
          ie: the ones in the task network, not the abstract ones in the spec.
        """
        assert(name in self.network)
        preds = self.network.pred[name]
        succ  = self.network.succ[name]
        return tomlguard.TomlGuard({
            "pred" : {"tasks": [x for x in preds if isinstance(x, DootTaskName)],
                      "artifacts": {"abstract": [x for x in preds if isinstance(x, DootTaskArtifact) and not x.is_concrete],
                                    "concrete": [x for x in preds if isinstance(x, DootTaskArtifact) and x.is_concrete]}},
            "succ" : {"tasks": [x for x in succ  if isinstance(x, DootTaskName) and x is not self._root_node],
                      "artifacts": {"abstract": [x for x in succ if isinstance(x, DootTaskArtifact) and not x.is_concrete],
                                    "concrete": [x for x in succ if isinstance(x, DootTaskArtifact) and x.is_concrete]}},
            "root" : self._root_node in succ,
            })

    def connect(self, left:None|DootTaskName|DootTaskArtifact, right:None|False|DootTaskName|DootTaskArtifact=None) -> None:
        """
        Connect a task node to another. left -> right
        If given left, None, connect left -> ROOT
        if given left, False, just add the node
        """
        logging.debug("Connecting: %s -> %s", left, right)
        match left:
            case DootTaskName() if left not in self.specs:
                raise doot.errors.DootTaskTrackingError("Can't connect a non-existent task", left)
            case DootTaskArtifact() if left not in self.artifacts:
                raise doot.errors.DootTaskTrackingError("Can't connect a non-existent artifact", left)
            case _ if left not in self.network.nodes:
                self._add_node(left)

        match right:
            case False:
                return
            case None:
                pass
            case DootTaskName() if right not in self.specs:
                raise doot.errors.DootTaskTrackingError("Can't connect a non-existent task", right)
            case DootTaskArtifact() if right not in self.artifacts:
                raise doot.errors.DootTaskTrackingError("Can't connect a non-existent artifact", right)
            case _ if right not in self.network.nodes:
                self._add_node(right)

        if right in self.network.succ[left]:
            # nothing to do
            return

        # Add the edge, with metadata
        match left, right:
            case DootTaskName(), None:
                self.network.add_edge(left, self._root_node, type=EDGE_E.TASK)
            case DootTaskName(), DootTaskName():
                self.network.add_edge(left, right, type=EDGE_E.TASK)
            case DootTaskName(), DootTaskArtifact():
                self.network.add_edge(left, right, type=EDGE_E.TASK_CROSS)
            case DootTaskArtifact(), DootTaskName():
                self.network.add_edge(left, right, type=EDGE_E.ARTIFACT_CROSS)
            case DootTaskArtifact(), DootTaskArtifact():
                self.network.add_edge(left, right, type=EDGE_E.ARTIFACT)

    def validate_network(self) -> bool:
        """ Finalise and ensure consistence of the task network.
        run tests to check the dependency graph is acceptable
        """
        logging.debug("Validating Task Network")
        if not nx.is_directed_acyclic_graph(self.network):
            raise doot.errors.DootTaskTrackingError("Network isn't a DAG")

        for node, data in self.network.nodes.items():
            match node:
                case DootTaskName() if not data[EXPANDED]:
                    raise doot.errors.DootTaskTrackingError("Network isn't fully expanded", node)
                case DootTaskName() if TaskFlags.CONCRETE not in node:
                    raise doot.errors.DootTaskTrackingError("Abstract Node in network", node)
                case DootTaskArtifact():
                    pass

    def build_network(self) -> None:
        """
        for each task queued (ie: connected to the root node)
        expand its dependencies and add into the network, until no mode nodes to expand.
        then connect concerete artifacts to abstract artifacts.

        # TODO network could be built in total, or on demand
        """
        logging.debug("Building Task Network")
        queue     = [x for x,y in self.network.pred[self._root_node].items() if not y.get(EXPANDED, False)]
        processed = { self._root_node }
        while bool(queue): # expand tasks
            logging.debug("Processing: %s", queue[0])
            match queue.pop():
                case x if x in processed or self.network.nodes[x].get(EXPANDED, False):
                    logging.debug("Processed already")
                    processed.add(x)
                case DootTaskName() as x:
                    additions = self._expand_task_node(x)
                    logging.debug("Task Expansion produced: %s", additions)
                    queue    += additions
                    processed.add(x)
                case DootTaskArtifact() as x:
                    additions = self._expand_artifact(x)
                    logging.debug("Artifact Expansion produced: %s", additions)
                    queue += additions
                    processed.add(x)
                    pass
        else:
            self._fixup_artifacts()
            logging.debug("Final Network Nodes: %s", self.network.nodes)
            logging.debug("Final Network Edges: %s", self.network.edges)
            pass

class _TrackerQueue_boltons:
    """ The _queue of tasks """

    def __init__(self):
        super().__init__()
        self.active_set        : list[DootTaskName|DootTaskArtifact]       = set()
        self.execution_trace   : list[str]                                 = []
        self._queue             : boltons.queueutils.HeapPriorityQueue      = boltons.queueutils.HeapPriorityQueue()

    def _maybe_implicit_queue(self, task:Task_i) -> None:
        """ tasks can be activated for running by a number of different conditions
          this handles that
          """
        if task.spec.name in self.active_set:
            return

        match task.spec.queue_behaviour:
            case TaskQueueMeta.auto:
                self.queue_task(task.fullname)
            case TaskQueueMeta.reactive:
                self.network.nodes[task.fullname][REACTIVE_ADD] = True
            case TaskQueueMeta.default:
                # Waits for explicit _queue
                pass
            case _:
                raise doot.errors.DootTaskTrackingError("Unknown _queue behaviour specified: %s", task.spec.queue_behaviour)

    def _reactive_queue(self, focus:str) -> None:
        """ Queue any known task in the network that auto-reacts to a focus """
        for adj in self.network.adj[focus]:
            if self.network.nodes[adj].get(REACTIVE_ADD, False):
                self.queue_task(adj, silent=True)

    def _reactive_fail_queue(self, focus:str) -> None:
        """ TODO: make reactive failure tasks that can be triggered from
          a tasks 'on_fail' collection
          """
        raise NotImplementedError()

    def deque(self) -> DootTaskName:
        """ remove the top task from the _queue """
        focus = self._queue.pop()
        self.tasks[focus].priority -= 1
        logging.debug("Task %s: Priority Decrement to: %s", focus, self.tasks[focus].priority)
        self.active_set.remove(focus)
        return focus

    def queue_task(self, name:str|DootTaskName|DootTaskSpec|Task_i) -> DootTaskName:
        """
          Queue a task by name|spec|Task_i.
          registers and specializes the relevant spec, inserts it into the network
          Does *not* rebuild the network
        """
        match name:
            case str() | DootTaskName() if name not in self.specs:
                raise doot.errors.DootTaskTrackingError("Can't _queue a non-existent task", name)
            case str() | DootTaskName() if name in self.concrete and bool(self.concrete[name]):
                instance = self.concrete[name][0]
                self._add_node(instance)
                t_name   = self._make_task(instance)
            case str() | DootTaskName() if name in self.tasks:
                t_name = DootTaskName.build(name)
            case str() | DootTaskName():
                assert(TaskFlags.CONCRETE not in DootTaskName.build(name))
                instance : DootTaskName = self._instantiate_spec(name)
                self._add_node(instance)
                t_name   = self._make_task(DootTaskName.build(name))
            case DootTaskSpec() as spec:
                self.register_spec(spec)
                self._add_node(spec.name)
                t_name = self._make_task(spec)
            case Task_i() as task if task.fullname not in self.tasks:
                t_name = task.fullname
                self.register_spec(task.spec)
                self._add_node(t_name)
                self.tasks[t_name] = task
            case _:
                raise doot.errors.DootTaskTrackingError("Unrecognized type given to queue", name)

        ## --

        assert(t_name in self.tasks)
        assert(t_name in self.specs)
        assert(TaskFlags.CONCRETE in self.specs[t_name].flags)
        self.active_set.add(t_name)
        self._queue.add(t_name, priority=self.tasks[t_name].priority)
        return t_name

    def clear_queue(self) -> None:
        """ Remove everything from the task _queue """
        # TODO _queue the task's failure/cleanup tasks
        self.active_set =  set()
        self.task_queue = boltons.queueutils.HeapPriorityQueue()

class BaseTracker(_TrackerStore, _TrackerNetwork, _TrackerQueue_boltons, TaskTracker_i):
    """ The public part of the standard tracker implementation """
    pass
