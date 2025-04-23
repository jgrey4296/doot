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
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Mixin, Proto

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._structs.relation_spec import RelationSpec
from doot.enums import ArtifactStatus_e, TaskMeta_e, TaskStatus_e
from doot.mixins.matching import TaskMatcher_m
from doot.structs import (ActionSpec, InjectSpec, TaskArtifact, TaskName, TaskSpec)
from doot.task.core.task import DootTask

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

    from jgdv.structs.chainguard import ChainGuard
    type Abstract[T] = T
    type Concrete[T] = T
    type ActionElem  = ActionSpec|RelationSpec
    type ActionGroup = list[ActionElem]
##--|
from doot._abstract import Task_p
# isort: on
# ##-- end types

##-- logging
logging          = logmod.getLogger(__name__)
logging.disabled = False
##-- end logging

##--|

class _Registration_m:

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
            if TaskMeta_e.DISABLED in spec.meta:
                logging.trace("Ignoring Registration of disabled task: %s", spec.name.readable)
                continue

            self.specs[spec.name] = spec
            logging.trace("Registered Spec: %s", spec.name)

            # Register the head and cleanup specs:
            if TaskMeta_e.JOB in spec.meta:
                queue += spec.gen_job_head()
            else:
                queue += spec.gen_cleanup_task()

            self._register_spec_artifacts(spec)
            self._register_blocking_relations(spec)

    def _register_artifact(self, art:TaskArtifact, *tasks:TaskName) -> None:
        logging.trace("Registering Artifact: %s, %s", art, tasks)
        self.artifacts[art].update(tasks)
        # Add it to the relevant abstract/concrete set
        if art.is_concrete():
            self._concrete_artifacts.add(art)
        else:
            self._abstract_artifacts.add(art)

    def _register_spec_artifacts(self, spec:TaskSpec) -> None:
        """ Register the artifacts in a spec """
        for rel in spec.action_group_elements():
            match rel:
                case RelationSpec(target=TaskArtifact() as art):
                    self._register_artifact(art, spec.name)
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
                case RelationSpec(target=target, relation=RelationSpec.mark_e.blocks) if spec.name.is_uniq():
                    logging.trace("Registering Requirement: %s : %s", target, rel.invert(spec.name))
                    rel.object = spec.name
                    self._blockers[target].append(rel)
                case _: # Ignore action specs and non
                    pass

class _Instantiation_m:

    def _get_task_source_chain(self, name:Abstract[TaskName]) -> list[Abstract[TaskSpec]]:
        """ get the chain of sources for a task.
          this traces from an instance back towards the root,
          returning [root, ... grandparent, parent, instance].

          traces with the *last* value in spec.sources.
        """
        match name:
            case TaskName():
                assert(not name.is_uniq())
            case TaskArtifact():
                assert(not name.is_concrete())
        spec                          = self.specs[name]
        chain   : list[TaskSpec]  = []
        current : Maybe[TaskSpec] = spec
        count   : int = API.INITIAL_SOURCE_CHAIN_COUNT
        while current is not None:
            if 0 > count:
                raise doot.errors.TrackingError("Building a source chain grew to large", name)
            count -= 1
            match current: # Determine the base
                case TaskSpec(name=name) if TaskMeta_e.JOB_HEAD in name:
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
                    raise doot.errors.TrackingError("Unknown spec customization attempt", spec, current, chain)

        chain.reverse()
        return chain

    def _maybe_reuse_instantiation(self, name:TaskName, *, add_cli:bool=False, extra:bool=False) -> Maybe[Concrete[TaskName]]:
        """ if an existing concrete spec exists, use it if it has no conflicts """
        if name not in self.specs:
            logging.detail("Not reusing instantiation because name doesn't have a matching spec: %s", name)
            return None
        if extra or add_cli:
            logging.detail("Not reusing instantiation because extra or cli args were requested: %s", name)
            return None

        if name.is_uniq():
            return name

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

    def _instantiate_spec(self, name:Abstract[TaskName], *, add_cli:bool=False, extra:Maybe[dict|ChainGuard]=None) -> Concrete[TaskName]:
        """ Convert an Asbtract Spec into a Concrete Spec,
          Reuses a existing concrete spec if possible.
          """
        match self._maybe_reuse_instantiation(name, add_cli=add_cli, extra=bool(extra)):
            case None:
                pass
            case TaskName() as existing:
                logging.detail("Reusing instantiation: %s for %s", existing, name)
                return existing

        spec = self.specs[name]
        # Instantiate the spec from its source chain
        match self._get_task_source_chain(name):
            case []:
                raise doot.errors.TrackingError("this shouldn't be possible", name)
            case [x]:
                # No chain, just instantiate the spec
                instance_spec = x.instantiate_onto(None)
            case [*xs]:
                # (reversed because the chain goes from spec -> ancestor)
                # and you want to instantiate descendents onto ancestors
                instance_spec = ftz.reduce(lambda x, y: y.instantiate_onto(x), xs)

        logging.detail("Instantiating: %s into %s", name, instance_spec.name)
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

    def _instantiate_relation(self, rel:RelationSpec, *, control:Concrete[TaskName]) -> Concrete[TaskName]:
        """ find a matching relendency/requirement according to a set of keys in the spec, or create a matching instance
          if theres no constraints, will just instantiate.

          """
        logging.trace("Instantiating Relation: %s - %s -> %s", control, rel.relation.name, rel.target)
        assert(control in self.specs)
        assert(rel.target in self.specs)
        control_spec              = self.specs[control]
        target_spec               = self.specs[rel.target]
        successful_matches        = []
        try:
            match InjectSpec.build(rel, sources=[control_spec]):
                case None:
                    extra = {}
                case x:
                    extra = x.as_dict(constraint=target_spec)
        except doot.errors.InjectionError as err:
            raise doot.errors.TrackingError(*err.args, control, rel) from None

        match self.concrete.get(rel.target, None):
            case [] | None if rel.target not in self.specs:
                raise doot.errors.TrackingError("Unknown target declared in Constrained Relation", control, rel.target)
            case [] | None:
                pass
            case [*xs] if not bool(rel.constraints) and not bool(rel.inject):
                successful_matches = [x for x in xs if x != control]
            case [*xs]:
                # concrete instances exist, match on them
                potentials : list[TaskSpec] = [self.specs[x] for x in xs]
                successful_matches += [x.name for x in potentials if self.match_with_constraints(x, control_spec, relation=rel)]

        match successful_matches:
            case []: # No matches, instantiate, with injected values
                instance : TaskName      = self._instantiate_spec(rel.target, extra=extra)
                if not self.match_with_constraints(self.specs[instance], control_spec, relation=rel):
                    raise doot.errors.TrackingError("Failed to build task matching constraints")
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

    def _make_task(self, name:Concrete[TaskName], *, task_obj:Maybe[Task_p]=None) -> Concrete[TaskName]:
        """ Build a Concrete Spec's Task object
          if a task_obj is provided, store that instead

          return the name of the task
          """
        if not isinstance(name, TaskName):
            raise doot.errors.TrackingError("Tried to add a not-task", name)
        if not name.is_uniq():
            raise doot.errors.TrackingError("Tried to add a task using a non-concrete spec", name)
        if name in self.tasks:
            return name

        logging.detail("Constructing Task Object: %s", name)
        match task_obj:
            case None:
                spec = self.specs[name]
                task : Task_p = spec.make()
            case Task_p():
                task = task_obj
            case _:
                raise doot.errors.TrackingError("Supplied task object isn't a task_i", task_obj)

        # Store it
        self.tasks[name] = task
        return name

##--|

@Mixin(_Registration_m, _Instantiation_m, TaskMatcher_m)
class TrackRegistry:
    """ Stores and manipulates specs, tasks, and artifacts """

    specs                : dict[TaskName, TaskSpec]
    concrete             : dict[Abstract[TaskName], list[Concrete[TaskName]]]
    # Invariant for tasks: every key in tasks has a matching key in specs.
    tasks                : dict[Concrete[TaskName], Task_p]
    artifacts            : dict[TaskArtifact, set[Abstract[TaskName]]]
    _artifact_status     : dict[TaskArtifact, TaskStatus_e]
    # Artifact sets
    _abstract_artifacts  : set[Abstract[TaskArtifact]]
    _concrete_artifacts  : set[Concrete[TaskArtifact]]
    # indirect blocking requirements:
    _blockers            : dict[Concrete[TaskName|TaskArtifact], list[RelationSpec]]

    def __init__(self):
        self.specs                = {}
        self.concrete             = defaultdict(lambda: [])
        self.tasks                = {}
        self.artifacts            = defaultdict(set)
        self._artifact_status     = defaultdict(lambda: ArtifactStatus_e.DECLARED)
        self._abstract_artifacts  = set()
        self._concrete_artifacts  = set()
        self._blockers            = defaultdict(lambda: [])

    def get_status(self, task:Concrete[TaskName|TaskArtifact]) -> TaskStatus_e|ArtifactStatus_e:
        """ Get the status of a task or artifact """
        match task:
            case TaskArtifact():
                return self._artifact_status[task]
            case TaskName() if task in self.tasks:
               return self.tasks[task].status
            case TaskName() if task in self.specs:
                return TaskStatus_e.DECLARED
            case _:
                return TaskStatus_e.NAMED

    def set_status(self, task:Concrete[TaskName|TaskArtifact]|Task_p, status:TaskStatus_e|ArtifactStatus_e) -> bool:
        """ update the state of a task in the dependency graph
          Returns True on status update,
          False on no task or artifact to update.
        """
        logging.trace("Updating State: %s -> %s", task, status)
        match task, status:
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
