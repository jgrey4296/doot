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

from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload, NewType,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract import (Job_i, Task_i, TaskRunner_i,
                            TaskTracker_i)
from doot._structs.relation_spec import RelationSpec
from doot.enums import TaskMeta_f, QueueMeta_e, TaskStatus_e, LocationMeta_f, RelationMeta_e, EdgeType_e, ArtifactStatus_e
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

ROOT                           : Final[str]                    = "root::_" # Root node of dependency graph
EXPANDED                       : Final[str]                    = "expanded"  # Node attribute name
REACTIVE_ADD                   : Final[str]                    = "reactive-add"
INITIAL_SOURCE_CHAIN_COUNT      : Final[int]                   = 10

T                                                              = TypeVar("T")
Abstract                                                       = NewType("Abstract", T)
Concrete                                                       = NewType("Concrete", T)

ActionElem                     : TypeAlias                     = ActionSpec|RelationSpec
ActionGroup                    : TypeAlias                     = list[ActionElem]

class TrackRegistry(Injector_m, TaskMatcher_m):
    """ Stores and manipulates specs, tasks, and artifacts """

    def __init__(self):
        self.specs                : dict[TaskName, TaskSpec]  = {}
        self.concrete             : dict[Abstract[TaskName], list[Concrete[TaskName]]]                 = defaultdict(lambda: [])
        self._transformer_specs   : dict[TaskArtifact, list[Abstract[TaskName]]]                       = defaultdict(lambda: [])
        # Invariant for tasks: every key in tasks has a matching key in specs.
        self.tasks                : dict[Concrete[TaskName], Task_i]                                   = {}
        self.artifacts            : dict[TaskArtifact, set[Abstract[TaskName]]]                        = defaultdict(set)
        self._artifact_status     : dict[TaskArtifact, TaskStatus_e]                                   = defaultdict(lambda: ArtifactStatus_e.DECLARED)
        # Artifact sets
        self._abstract_artifacts  : set[Abstract[TaskArtifact]]                                        = set()
        self._concrete_artifacts  : set[Concrete[TaskArtifact]]                                        = set()
        # indirect blocking requirements:
        self._blockers            : dict[Concrete[TaskName|TaskArtifact], list[RelationSpec]]          = defaultdict(lambda: [])

    def register_spec(self, *specs:TaskSpec) -> None:
        """ Register task specs, abstract or concrete.
        An initial concrete instance will be created for any abstract spec.
        """
        queue = []
        queue += specs
        while bool(queue):
            spec = queue.pop(0)
            if spec.name in self.specs:
                continue
            if TaskMeta_f.DISABLED in spec.flags:
                logging.debug("Ignoring Registration of disabled task: %s", spec.name.readable)
                continue

            self.specs[spec.name] = spec
            logging.debug("Registered Spec: %s", spec.name)

            # Register the head and cleanup specs:
            if TaskMeta_f.JOB in spec.flags:
                queue += spec.gen_job_head()
            else:
                queue.append(spec.gen_cleanup_task())

            self._register_spec_artifacts(spec)
            self._register_transformer(spec)
            self._register_blocking_relations(spec)

    def get_status(self, task:Concrete[TaskName|TaskArtifact]) -> TaskStatus_e|ArtifactStatus_e:
        """ Get the status of a task or artifact """
        match task:
            case TaskArtifact():
                return self._artifact_status[task]
            case TaskName() if task in self.tasks:
               return self.tasks[task].status
            # case TaskName() if task in self.network:
            #     return TaskStatus_e.DEFINED
            case TaskName() if task in self.specs:
                return TaskStatus_e.DECLARED
            case _:
                return TaskStatus_e.NAMED

    def set_status(self, task:Concrete[TaskName|TaskArtifact]|Task_i, status:TaskStatus_e|ArtifactStatus_e) -> bool:
        """ update the state of a task in the dependency graph
          Returns True on status update,
          False on no task or artifact to update.
        """
        logging.debug("Updating State: %s -> %s", task, status)
        match task, status:
            # case TaskName(), _ if task == self._root_node:
            #     return False
            case Task_i(), TaskStatus_e() if task.name in self.tasks:
                self.tasks[task.name].status = status
            case TaskArtifact(), ArtifactStatus_e():
                self._artifact_status[task] = status
            case TaskName(), TaskStatus_e() if task in self.tasks:
                self.tasks[task].status = status
            case TaskName(), TaskStatus_e():
                logging.debug("Not Setting Status of %s, its hasn't been started", task)
                return False
            case _, _:
                raise doot.errors.DootTaskTrackingError("Bad task update status args", task, status)

        return True

    def _register_transformer(self, spec:TaskSpec):
        """ register a transformers pre and post targets """
        match spec.transformer_of():
            case None:
                pass
            case (pre, post):
                logging.debug("Registering Transformer: %s -> (%s) -> %s", pre, spec.name.readable, post)
                self._transformer_specs[pre.target].append(spec.name)
                self._transformer_specs[post.target].append(spec.name)


    def _register_artifact(self, art:TaskArtifact, *tasks:TaskName):
        logging.debug("Registering Artifact: %s, %s", art, tasks)
        self.artifacts[art].update(tasks)
        # Add it to the relevant abstract/concrete set
        if not art.is_concrete():
            self._abstract_artifacts.add(art)
        else:
            self._concrete_artifacts.add(art)

    def _register_spec_artifacts(self, spec:TaskSpec) -> None:
        """ Register the artifacts in a spec """
        for rel in spec.action_group_elements():
            match rel:
                case RelationSpec(target=TaskArtifact() as art):
                    self._register_artifact(art, spec.name)
                case _:
                    pass

    def _register_blocking_relations(self, spec:TaskSpec):
        if spec.name.is_uniq:
            # If the spec is instantiated,
            # it has no indirect relations
            return

        # Register Indirect dependencies:
        # So if spec blocks target,
        # record that target needs spec
        for rel in spec.action_group_elements():
            match rel:
                case RelationSpec(target=target, relation=RelationMeta_e.blocks) if spec.name.is_uniq:
                    logging.debug("Registering Requirement: %s : %s", target, rel.invert(spec.name))
                    rel.object = spec.name
                    self._blockers[target].append(rel)
                case _: # Ignore action specs and non
                    pass

    def _maybe_reuse_instantiation(self, name:TaskName, *, add_cli:bool=False, extra:bool=False) -> None|Concrete[TaskName]:
        """ if an existing concrete spec exists, use it if it has no conflicts """
        if name not in self.specs:
            logging.debug("Not reusing instantiation because name doesn't have a matching spec: %s", name)
            return None
        if extra or add_cli:
            logging.debug("Not reusing instantiation because extra or cli args were requested: %s", name)
            return None

        if name.is_uniq:
            return name

        if not bool(self.concrete[name]):
            logging.debug("Not reusing instantiation because there is no instantiation to reuse: %s", name)
            return None

        abstract = self.specs[name]
        match [x for x in self.concrete[name] if abstract != (concrete:=self.specs[x]) and self.match_with_constraints(concrete, abstract)]:
            case []:
                logging.debug("Not reusing instantiation because existing specs dont match with constraints: %s", name)
                return None
            case [x, *xs]:
                logging.debug("Reusing Concrete Spec: %s for %s", x, name)
                # Can use an existing concrete spec
                return x

    def _instantiate_spec(self, name:Abstract[TaskName], *, add_cli:bool=False, extra:None|dict|ChainGuard=None) -> Concrete[TaskName]:
        """ Convert an Asbtract Spec into a Concrete Spec,
          Reuses a existing concrete spec if possible.
          """
        match self._maybe_reuse_instantiation(name, add_cli=add_cli, extra=bool(extra)):
            case None:
                pass
            case TaskName() as existing:
                track_l.debug("Reusing instantiation: %s for %s", existing, name)
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

        track_l.debug("Instantiating: %s into %s", name, instance_spec.name)
        assert(instance_spec is not None)
        if add_cli:
            # only add cli args explicitly. ie: when the task has been queued by the user
            instance_spec = instance_spec.apply_cli_args()

        if extra:
            # apply additional settings onto the instance
            instance_spec = instance_spec.specialize_from(extra)

        assert(instance_spec.name.is_uniq)
        # Map abstract -> concrete
        self.concrete[name].append(instance_spec.name)
        # register the actual concrete spec
        self.register_spec(instance_spec)

        assert(instance_spec.name in self.specs)
        return instance_spec.name

    def _instantiate_relation(self, rel:RelationSpec, *, control:Concrete[TaskName]) -> Concrete[TaskName]:
        """ find a matching relendency/requirement according to a set of keys in the spec, or create a matching instance
          if theres no constraints, will just instantiate.
          """
        logging.warning("Instantiating Relation: %s - %s -> %s", control, rel.relation.name, rel.target)
        assert(control in self.specs)
        assert(rel.target in self.specs)
        control_spec              = self.specs[control]
        target_spec               = self.specs[rel.target]
        successful_matches        = []
        match self.concrete.get(rel.target, None):
            case [] | None if rel.target not in self.specs:
                raise doot.errors.DootTaskTrackingError("Unknown target declared in Constrained Relation", control, rel.target)
            case [] | None:
                pass
            case [*xs] if not bool(rel.constraints) and not bool(rel.inject):
                successful_matches = [x for x in xs if x != control]
            case [*xs]:
                # concrete instances exist, match on them
                potentials : list[TaskSpec] = [self.specs[x] for x in xs]
                successful_matches += [x.name for x in potentials if self.match_with_constraints(x, control_spec, relation=rel)]

        match successful_matches:
            case []: # No matches, instantiate
                extra    : None|dict      = self.build_injection(rel, control_spec, constraint=target_spec)
                instance : TaskName      = self._instantiate_spec(rel.target, extra=extra)
                if not self.match_with_constraints(self.specs[instance], control_spec, relation=rel):
                    raise doot.errors.DootTaskTrackingError("Failed to build task matching constraints")
                logging.warning("Using New Instance: %s", instance)
                return instance
            case [x]: # One match, connect it
                assert(x in self.specs)
                assert(x.is_uniq)
                instance : TaskName = x
                logging.warning("Reusing Instance: %s", instance)
                return instance
            case [*xs, x]: # TODO check this.
                # Use most recent instance?
                assert(x in self.specs)
                assert(x.is_uniq)
                instance : TaskName = x
                logging.warning("Reusing latest Instance: %s", instance)
                return instance

    def _instantiate_transformer(self, name:Abstract[TaskNAme], artifact:TaskArtifact) -> None|Concrete[TaskName]:
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

    def _make_task(self, name:Concrete[TaskName], *, task_obj:Task_i=None) -> ConcreteId:
        """ Build a Concrete Spec's Task object
          if a task_obj is provided, store that instead

          return the name of the task
          """
        if not isinstance(name, TaskName):
            raise doot.errors.DootTaskTrackingError("Tried to add a not-task", name)
        if not name.is_uniq:
            raise doot.errors.DootTaskTrackingError("Tried to add a task using a non-concrete spec", name)
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

    def _get_task_source_chain(self, name:Abstract[TaskName]) -> list[Abstract[TaskSpec]]:
        """ get the chain of sources for a task.
          this traces from an instance back towards the root,
          returning [root, ... grandparent, parent, instance].

          traces with the *last* value in spec.sources.
        """
        match name:
            case TaskName():
                assert(not name.is_uniq)
            case TaskArtifact():
                assert(not name.is_concrete())
        spec                          = self.specs[name]
        chain   : list[TaskSpec]  = []
        current : None|TaskSpec   = spec
        count   : int = INITIAL_SOURCE_CHAIN_COUNT
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
