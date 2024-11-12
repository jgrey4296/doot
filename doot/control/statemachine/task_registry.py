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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
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
INITIAL_SOURCE_CHAIN_COUNT      : Final[int]                  = 10

AbstractId                     : TypeAlias                   = TaskName|TaskArtifact
ConcreteId                     : TypeAlias                   = TaskName|TaskArtifact
AnyId                          : TypeAlias                   = TaskName|TaskArtifact
AbstractSpec                   : TypeAlias                   = TaskSpec
ConcreteSpec                   : TypeAlias                   = TaskSpec
AnySpec                        : TypeAlias                   = TaskSpec

ActionElem                     : TypeAlias                   = ActionSpec|RelationSpec
ActionGroup                    : TypeAlias                   = list[ActionElem]

class TaskRegistry:
    """ Stores and manipulates specs, tasks, and artifacts """

    def __init__(self):
        # All [Abstract, Concrete] Specs:
        self.specs                : dict[AnyId, AnySpec]                          = {}
        # Mapping (Abstract Spec) -> Concrete Specs. Every id, abstract and concerete, has a spec in specs.
        self.concrete             : dict[AbstractId, list[ConcreteId]]            = defaultdict(lambda: [])
        # Mapping Artifact -> list[Spec] of solo transformer specs. Every abstractId has a spec in specs.
        self._transformer_specs   : dict[TaskArtifact, list[AbstractId]]          = defaultdict(lambda: [])
        # All (Concrete Specs) Task objects. Invariant: every key in tasks has a matching key in specs.
        self.tasks                : dict[ConcreteId, Task_i]                      = {}
        # Artifact -> list[TaskName] of related tasks
        self.artifacts            : dict[TaskArtifact, list[AbstractId]]          = defaultdict(set)
        self._artifact_status     : dict[TaskArtifact, TaskStatus_e]              = defaultdict(lambda: TaskStatus_e.ARTIFACT)
        # Artifact sets
        self._abstract_artifacts  : set[TaskArtifact]                             = set()
        self._concrete_artifacts  : set[TaskArtifact]                             = set()
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

    def _instantiate_spec(self, name:AbstractId, *, add_cli:bool=False, extra:None|dict|tomlguard.TomlGuard=None) -> ConcreteId:
        """ Convert an Asbtract Spec into a Concrete Spec,
          Reuses a existing concrete spec if possible.
          """
        match self._maybe_reuse_instantiation(name, add_cli=add_cli, extra=bool(extra)):
            case None:
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
            instance_spec = instance_spec.apply_cli_args()

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

    def _instantiate_relation(self, rel:RelationSpec, *, control:ConcreteId) -> ConcreteId:
        """ find a matching relendency/requirement according to a set of keys in the spec, or create a matching instance
          if theres no constraints, will just instantiate.
          """
        logging.debug("Instantiating Relation: %s - %s -> %s", control, rel.relation.name, rel.target)
        assert(control in self.specs)
        control_spec              = self.specs[control]
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
                potentials : list[TaskSpec] = [self.specs[x] for x in xs if x != control]
                successful_matches += [x.name for x in potentials if x.match_with_constraints(control_spec, relation=rel)]

        match successful_matches:
            case []: # No matches, instantiate
                extra    : None|dict     = control_spec.build_injection(rel)
                instance : TaskName      = self._instantiate_spec(rel.target, extra=extra)
                if not self.specs[instance].match_with_constraints(control_spec, relation=rel):
                    raise doot.errors.DootTaskTrackingError("Could not instantiate a spec that passes constraints", rel, control)
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

        for rel in spec.action_group_elements():
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
            for rel in spec.action_group_elements():
                match rel:
                    case RelationSpec(target=target, relation=RelationMeta_e.req) if TaskMeta_f.CONCRETE not in spec.name:
                        logging.debug("Registering Requirement: %s : %s", target, rel.invert(spec.name))
                        self._requirements[target].append(rel.invert(spec.name))
                    case _: # Ignore action specs
                        pass

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
