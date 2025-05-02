 #!/usr/bin/env python3
"""

"""
# mypy: disable-error-code="attr-defined"
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
from doot.structs import (ActionSpec, InjectSpec, TaskArtifact, TaskName, TaskSpec)
from doot.task.core.task import DootTask

# ##-- end 1st party imports

from . import _interface as API # noqa: N812
from doot._structs import _interface as S_API  # noqa: N812

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
##
from doot._abstract import Task_p, Task_d
# isort: on
# ##-- end types

##-- logging
logging          = logmod.getLogger(__name__)
logging.disabled = False
##-- end logging

##--|

class _RegistryData:
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
    _late_injections     : dict[Concrete[TaskName], tuple[InjectSpec, TaskName]]

class _Registration_m(_RegistryData):

    def register_spec(self, *specs:TaskSpec) -> None:
        """ Register task specs, abstract or concrete

        An initial concrete instance will be created for any abstract spec.

        Specs with names ending in <partial> will apply their direct .sources predecessor
        under themselves, and pop off the 'partial' name
        That predecessor can not be partial itself
        """
        queue : list[TaskSpec] = []
        queue += specs
        while bool(queue):
            spec = queue.pop(0)
            if spec.name in self.specs:
                continue
            if TaskMeta_e.DISABLED in spec.meta:
                logging.info("[Disabled] task: %s", spec.name.readable)
                continue
            if spec.name[-1] == "<partial>":
                spec = self._reify_partial_spec(spec)

            self.specs[spec.name] = spec
            match spec.name.is_uniq():
                case True:
                    logging.info("[+] Concrete Spec: %s", spec.name.readable)
                case False:
                    logging.info("[+] Abstract Spec: %s", spec.name)

            # Register the head and cleanup specs:
            if TaskMeta_e.JOB in spec.meta:
                queue += spec.gen_job_head()
            else:
                queue += spec.gen_cleanup_task()

            self._register_spec_artifacts(spec)
            self._register_blocking_relations(spec)
        else:
            pass

    def _reify_partial_spec(self, spec:TaskSpec) -> TaskSpec:
        """ Take a partial spec a.b.c..<partial>,
        Apply it over
        """
        adjusted_name = spec.name.pop() # type: ignore
        if adjusted_name in self.specs:
            raise ValueError("Tried to reify a partial spec into one that already is registered")

        base_name = spec.sources[-1]
        assert(isinstance(base_name, TaskName))
        match self.specs.get(base_name, None):
            case TaskSpec() as base_spec:
                return spec.reify_partial(base_spec)
            case _:
                raise ValueError("No Base Spec for Partial", spec.name, base_name)

    def _register_artifact(self, art:TaskArtifact, *tasks:TaskName) -> None:
        logging.info("[+] Artifact: %s, %s", art, tasks)
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
                    logging.info("[Requirement]: %s : %s", target, rel.invert(spec.name))
                    rel.object = spec.name
                    self._blockers[target].append(rel)
                case _: # Ignore action specs and non
                    pass

    def _register_late_injection(self, task:TaskName, inject:InjectSpec, parent:TaskName) -> None:
        """ Register an injection to run on task initialisation,
        using the state injection's from its parent
        """
        assert(task not in self._late_injections)
        self._late_injections[task] = (inject, parent)

class _Instantiation_m(_RegistryData):

    def _get_task_source_chain(self, name:Abstract[TaskName]) -> list[Abstract[TaskSpec]]:
        """ get the chain of sources for a task.
          this traces from an instance back towards the root,
          returning [root, ... grandparent, parent, instance].

          traces with the *last* value in spec.sources.
        """
        spec    : TaskSpec
        chain   : list[TaskSpec]
        current : Maybe[TaskSpec]
        count   : int

        assert(not name.is_uniq())
        spec    = self.specs[name]
        chain   = []
        current = spec
        count   = API.INITIAL_SOURCE_CHAIN_COUNT
        while current is not None:
            if 0 > count:
                raise doot.errors.TrackingError("Building a source chain grew to large", name)
            count -= 0
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
        no_spec       = name not in self.specs
        invalid_reuse = extra or add_cli
        uniq_spec     = name.is_uniq()
        no_instances  = not bool(self.concrete[name])

        return None

    def _instantiate_spec(self, name:Abstract[TaskName], *, add_cli:bool=False, extra:Maybe[dict|ChainGuard]=None) -> Concrete[TaskName]:
        """ Convert an Asbtract Spec into a Concrete Spec,
          Reuses a existing concrete spec if possible.
          """
        match self._maybe_reuse_instantiation(name, add_cli=add_cli, extra=bool(extra)):
            case None:
                pass
            case TaskName() as existing:
                logging.debug("[Reuse] Spec %s for %s", existing.readable, name)
                return existing

        spec          = self.specs[name]
        instance_spec = spec.instantiate()

        logging.debug("[Instance] %s into %s", name, instance_spec.name.readable)
        assert(instance_spec is not None)
        if add_cli:
            # only add cli args explicitly. ie: when the task has been queued by the user
            instance_spec = instance_spec.apply_cli_args()

        if extra:
            # apply additional settings onto the instance
            instance_spec = instance_spec.under(extra)

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
        logging.debug("[Relation]: %s -> %s -> %s", control.readable, rel.relation.name, rel.target)
        assert(control in self.specs)
        if rel.target not in self.specs:
            raise doot.errors.TrackingError("Unknown target declared in Constrained Relation", control, rel.target)

        assert(isinstance(rel.target, TaskName))
        control_spec       : TaskSpec       = self.specs[control]
        target_spec        : TaskSpec       = self.specs[rel.target]
        successful_matches : list[TaskName] = []
        instance           : TaskName
        existing           : TaskName

        for existing in self.concrete.get(rel.target, []):
            if not rel.accepts(control_spec, self.specs[existing]):
                # Constraint or Inject mismatch
                continue

            return existing
        else:
            # make a new rel.target instance
            match rel.inject:
                case InjectSpec() as inj:
                    injection = inj.apply_from_spec(control_spec)
                    instance = self._instantiate_spec(rel.target, extra=injection)
                    self._register_late_injection(instance, inj, control)
                    return instance
                case _:
                    return self._instantiate_spec(rel.target)

    def _make_task(self, name:Concrete[TaskName], *, task_obj:Maybe[Task_p]=None) -> Concrete[TaskName]:
        """ Build a Concrete Spec's Task object
          if a task_obj is provided, store that instead

          return the name of the task
          """
        task : Task_d

        if not isinstance(name, TaskName):
            raise doot.errors.TrackingError("Tried to add a not-task", name)
        if not name.is_uniq():
            raise doot.errors.TrackingError("Tried to add a task using a non-concrete spec", name)
        if name in self.tasks:
            return name

        logging.debug("[Instance] Task Object: %s", name)
        match task_obj:
            case None:
                spec = self.specs[name]
                task = spec.make()
            case Task_d():
                task = task_obj
            case _:
                raise doot.errors.TrackingError("Supplied task object isn't a task_i", task_obj)

        match self._late_injections.get(name, None):
            case InjectSpec() as inj, TaskName() as control:
                task.state |= inj.apply_from_state(self.tasks[control])
            case _:
                pass

        must_inject = spec.extra.on_fail([])[S_API.MUST_INJECT_K]()
        match [x for x in must_inject if x not in task.state]:
            case []:
                pass
            case xs:
                raise doot.errors.TrackingError("Task did not receive required injections", spec.name, xs)

        # Store it
        self.tasks[name] = task
        return name

##--|

@Mixin(_Registration_m, _Instantiation_m)
class TrackRegistry(_RegistryData):
    """ Stores and manipulates specs, tasks, and artifacts """

    def __init__(self):
        self.specs                = {}
        self.concrete             = defaultdict(lambda: [])
        self.tasks                = {}
        self.artifacts            = defaultdict(set)
        self._artifact_status     = defaultdict(lambda: ArtifactStatus_e.DECLARED)
        self._abstract_artifacts  = set()
        self._concrete_artifacts  = set()
        self._blockers            = defaultdict(lambda: [])
        self._late_injections     = {}

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

    def set_status(self, target:Concrete[TaskName|TaskArtifact]|Task_p, status:TaskStatus_e|ArtifactStatus_e) -> bool:
        """ update the state of a task in the dependency graph
          Returns True on status update,
          False on no task or artifact to update.
        """
        match target, status:
            case Task_p() as task, TaskStatus_e() if task.name in self.tasks:
                logging.info("[%s] %s -> %s", task.name.readable, self.get_status(task.name), status)
                self.tasks[task.name].status = status
            case TaskName() as task, TaskStatus_e() if task in self.tasks:
                logging.info("[%s] %s -> %s", task.readable, self.get_status(task), status)
                self.tasks[task].status = status
            case TaskArtifact() as art, ArtifactStatus_e():
                logging.info("[%s] %s -> %s", tart, self.get_status(art), status)
                self._artifact_status[art] = status
            case TaskName(), TaskStatus_e():
                logging.debug("[%s] Not Started Yet", task)
                return False
            case _, _:
                raise doot.errors.TrackingError("Bad task update status args", task, status)

        return True

    def get_priority(self, target:Concrete[TaskName|TaskArtifact]) -> int:
        match target:
            case TaskName() if target in self.tasks:
                return self.tasks[target].priority
            case _:
                return API.DECLARE_PRIORITY
