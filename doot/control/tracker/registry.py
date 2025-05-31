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
from doot.workflow._interface import ArtifactStatus_e, TaskMeta_e, TaskStatus_e
from doot.workflow import (ActionSpec, InjectSpec, TaskArtifact, TaskName, TaskSpec, RelationSpec, DootTask)

# ##-- end 1st party imports

from .. import _interface as API # noqa: N812
from doot.workflow import _interface as S_API  # noqa: N812

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
from doot.workflow._interface import Task_p
# isort: on
# ##-- end types

##-- logging
logging          = logmod.getLogger(__name__)
logging.disabled = False
##-- end logging

##--|

class _Registry_d:
    """
    Data used in the registry

    Invariants:
    - every key in tasks has a matching key in specs.
    - every concrete spec is in concrete under its abstract name
    - every implicit task that hasn't been registered is in implicit, mapped to its declaring spec
    """
    specs                : dict[TaskName, TaskSpec]
    concrete             : dict[Abstract[TaskName], list[Concrete[TaskName]]]
    implicit             : dict[Abstract[TaskName], TaskName]
    tasks                : dict[Concrete[TaskName], Task_p]
    artifacts            : dict[TaskArtifact, set[Abstract[TaskName]]]
    # Artifact sets
    abstract_artifacts  : set[Abstract[TaskArtifact]]
    concrete_artifacts  : set[Concrete[TaskArtifact]]
    # indirect blocking requirements:
    blockers            : dict[Concrete[TaskName|TaskArtifact], list[RelationSpec]]
    late_injections     : dict[Concrete[TaskName], tuple[InjectSpec, TaskName]]

    def __init__(self):
        self.specs                = {}
        self.concrete             = defaultdict(list)
        self.implicit             = {}
        self.tasks                = {}
        self.artifacts            = defaultdict(set)
        self.abstract_artifacts   = set()
        self.concrete_artifacts   = set()
        self.artifact_builders    = defaultdict(list)
        self.artifact_consumers   = defaultdict(list)
        self.blockers             = defaultdict(list)
        self.late_injections      = {}

class _Registration_m(_Registry_d):

    def register_spec(self, *specs:TaskSpec) -> None:
        """ Register task specs, abstract or concrete

        An initial concrete instance will be created for any abstract spec.

        Specs with names ending in <partial> will apply their direct .sources predecessor
        under themselves, and pop off the 'partial' name
        That predecessor can not be partial itself
        """
        registered : int
        queue : list[TaskSpec]

        registered = 0
        queue      = list(specs)
        while bool(queue):
            spec = queue.pop(0)
            if TaskMeta_e.DISABLED in spec.meta:
                logging.info("[Disabled] task: %s", spec.name[:])
                continue

            match spec.name:
                case TaskName() as x if x in self.specs:
                    if self.specs[x] is not spec:
                        raise ValueError("Tried to overwrite a spec", spec.name)
                    continue
                case TaskName() as x if x[-1] == "<partial>":
                    logging.info("[+.Partial] : %s", spec.name[:])
                    spec = self._reify_partial_spec(spec)
                case TaskName() if x.uuid(): # type: ignore
                    logging.info("[+.Concrete] : %s", spec.name)
                case TaskName():
                    logging.info("[+.Abstract] : %s", spec.name)

            self.specs[spec.name] = spec
            self._register_spec_artifacts(spec)
            if spec.name.uuid():
                self.concrete[spec.name.de_uniq()].append(spec.name)
                # Only concrete specs generate extra
                queue += spec.generate_specs()
            else:
                self._register_blocking_relations(spec)
                self._register_implicit_spec_names(spec)

            registered += 1
        else:
            # logging.debug("[+] %s new", registered)
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

    def _register_spec_artifacts(self, spec:TaskSpec) -> None:
        """ Register the artifacts a spec produces """
        for rel in spec.action_group_elements():
            match rel:
                case RelationSpec(target=TaskArtifact() as art, relation=reltype):
                    self._register_artifact(art, spec.name, relation=reltype)
                case _:
                    pass

    def _register_artifact(self, art:TaskArtifact, *tasks:TaskName, relation:Maybe[S_API.RelationMeta_e]=None) -> None:
        logging.info("[+] Artifact: %s, %s", art, tasks)
        self.artifacts[art].update(tasks)
        # Add it to the relevant abstract/concrete set
        if art.is_concrete():
            self.concrete_artifacts.add(art)
        else:
            self.abstract_artifacts.add(art)
        match relation:
            case None:
                pass
            case S_API.RelationMeta_e.needs:
                self.artifact_consumers[art] += tasks
            case S_API.RelationMeta_e.blocks:
                self.artifact_builders[art] += tasks

    def _register_blocking_relations(self, spec:TaskSpec) -> None:
        """ a Task[required_for=[x,y,z] blocks x,y,z,
        but if you just look at x,y,z, you can't know that.
        This is the reverse mapping to allow for that

        """
        assert(not spec.name.uuid())

        # Register Indirect dependencies:
        # So if spec blocks target,
        # record that target needs spec
        for rel in spec.action_group_elements():
            match rel:
                case RelationSpec(target=target, relation=RelationSpec.mark_e.blocks) if spec.name.uuid():
                    logging.info("[Requirement]: %s : %s", target, rel.invert(spec.name))
                    rel.object = spec.name
                    self.blockers[target].append(rel)
                case _: # Ignore action specs and non
                    pass
        else:
            return

    def _register_implicit_spec_names(self, spec:TaskSpec) -> None:
        is_job      = (TaskMeta_e.JOB in spec.meta
                       and not spec.name.is_head())
        has_cleanup = not (spec.name.is_cleanup() or is_job)
        if is_job:
            head = spec.name.with_head()
            assert(head not in self.implicit)
            self.implicit[head] = spec.name

        if has_cleanup:
            cleanup = spec.name.with_cleanup()
            assert(cleanup not in self.implicit)
            self.implicit[cleanup] = spec.name




    def _register_late_injection(self, task:TaskName, inject:InjectSpec, parent:TaskName) -> None:
        """ Register an injection to run on task initialisation,
        using the state injection's from its parent
        """
        logging.info("[Injection] Registering: %s <- %s", task, parent)
        if not bool(inject.from_state):
            return
        assert(task not in self.late_injections), (task, parent)
        assert(parent in self.specs)
        self.late_injections[task] = (inject, parent)

class _Instantiation_m(_Registry_d):

    def _instantiate_spec(self, name:Abstract[TaskName], *, extra:Maybe[dict|ChainGuard|bool]=None) -> Maybe[Concrete[TaskName]]:
        """ Convert an Asbtract Spec into a Concrete Spec,
          Reuses a existing concrete spec if possible.

        If extra=True, forces a new instance to be made
        If extra=False, blocks new instances from being made
        """
        match name:
            case _ if extra is True:
                name = name.de_uniq()
            case x if extra is False and x.uuid() and x in self.specs:
                return name
            case x if extra is False:
                return None
            case TaskName() as x if not x.uuid():
                pass
            case TaskName() as x if x in self.specs:
                logging.info("[Instance.Uniq] %s", x)
                return x
            case TaskName() as x:
                raise ValueError("Tried to instantiate a unique taskname", name)

        match self.concrete.get(name, []):
            case []:
                pass
            case _ if extra:
                pass
            case [x, *xs]:
                logging.info("[Instance.Concrete] : %s", x)
                return x

        spec          = self.specs[name]
        instance_spec = spec.instantiate()
        assert(instance_spec is not None)
        match extra:
            case None | True:
                pass
            case dict():
                # apply additional settings onto the instance
                instance_spec = instance_spec.under(extra)

        assert(instance_spec.name.uuid())
        logging.debug("[Instance.new] %s into %s", name, instance_spec.name)
        # register the actual concrete spec
        self.register_spec(instance_spec)

        assert(instance_spec.name in self.specs)
        return instance_spec.name

    def _instantiate_relation(self, rel:RelationSpec, *, control:Concrete[TaskName]) -> Concrete[TaskName]:
        """ find a matching relation according to constraints,
            or create a new instance if theres no constraints/no match

        returns the concrete TaskName of the instanced target of the relation
        """
        control_obj : Task_p|TaskSpec
        instance    : TaskName
        existing    : TaskName
        ##--|
        logging.debug("[Instance.Relation] : %s -> %s -> %s", control, rel.relation.name, rel.target)
        if control not in self.specs:
            raise doot.errors.TrackingError("Unknown control used in relation", control, rel)
        if rel.target not in self.specs and rel.target not in self.concrete:
            raise doot.errors.TrackingError("Unknown target declared in Constrained Relation", control, rel.target)

        assert(isinstance(rel.target, TaskName))
        if rel.target.uuid() and rel.target in self.specs:
            logging.debug("[Instance.Relation.Exists] : %s", rel.target)
            return rel.target

        control_obj = self.tasks.get(control, None) or self.specs[control] # type: ignore[arg-type]
        potentials  = self.concrete.get(rel.target, [])
        for existing in potentials:
            if not rel.accepts(control_obj, self.tasks.get(existing, None) or self.specs[existing]):
                continue
            logging.debug("[Instance.Relation.Match] : %s", existing)
            return existing
        else:
            # make a new rel.target instance
            match rel.inject:
                case InjectSpec() as inj:
                    current = self.concrete.get(rel.target, [])[:]
                    match inj.apply_from_spec(control_obj):
                        case dict() as x if not bool(x):
                            injection = True
                        case x:
                            injection = x
                    instance  = self._instantiate_spec(rel.target, extra=injection)
                    if not inj.validate(control_obj, self.specs[instance], only_spec=True):
                        raise doot.errors.TrackingError("Injection did not succeed", inj.validate_details(control_obj, self.specs[instance], only_spec=True))
                    assert(instance is not None)
                    assert(instance not in current)
                    self._register_late_injection(instance, inj, control)
                    logging.debug("[Instance.Relation.Inject] : %s", instance)
                    return instance
                case _:
                    instance = self._instantiate_spec(rel.target, extra=True)
                    assert(instance is not None)
                    logging.debug("[Instance.Relation.Basic] : %s", instance)
                    return instance

    def _make_task(self, name:Concrete[TaskName], *, task_obj:Maybe[Task_p]=None, parent:Maybe[Concrete[TaskName]]=None) -> Concrete[TaskName]:
        """ Build a Concrete Spec's Task object
          if a task_obj is provided, store that instead

          return the name of the task
          """
        task : Task_p

        match name, task_obj:
            case TaskName() as x, _ if not x.uuid():
                raise doot.errors.TrackingError("Tried to build a task using a non-concrete spec", name)
            case TaskName() as x, Task_p() as obj if x not in self.tasks:
                self.tasks[x] = obj
                return x
            case TaskName() as x, Task_p() as obj:
                raise doot.errors.TrackingError("Tried to provide a task object for already existing task", name)
            case TaskName() as x, _ if x not in self.specs:
                raise doot.errors.TrackingError("Tried to make a task from a non-existent spec name", name)
            case TaskName() as x, _ if x in self.tasks:
                return x
            case TaskName() as x, _ if x not in self.tasks:
                pass
            case name, _:
                raise doot.errors.TrackingError("Tried to make a task from a not-task name", name, task_obj)

        logging.debug("[Instance] Task Object: %s", name)
        spec = self.specs[name]
        match self.late_injections.get(name, None):
            case None:
                late_inject = None
            case _, TaskName() as x if x not in self.tasks:
                raise ValueError("Late Injection source is not a task", str(x))
            case InjectSpec() as inj, TaskName() as control:
                late_inject = (inj, self.tasks[control])

        match parent:
            case None:
                task = spec.make(ensure=Task_p, inject=late_inject)
            case TaskName() as x:
                task = spec.make(ensure=Task_p, inject=late_inject, parent=self.tasks.get(x, None))

        # Store it
        self.tasks[name] = task
        return name

class _Verification_m(_Registry_d):

    def verify(self, strict:bool=True) -> bool:
        failures = []
        for k, vals in self.concrete.items():
            if k not in self.specs:
                failures.append(f"Abstract Spec {k} is missing")
            match [x for x in vals if x not in self.specs]:
                case []:
                    pass
                case [*xs]:
                    failures.append(f"Concrete Specs are Missing: {xs}")

        for k, v in self.implicit.items():
            if v not in self.specs:
                failures.append(f"Implicit Spec {k} is missing its source {v}")

        # TODO Add more verify heuristics
        if not bool(failures):
            return True
        if strict:
            raise ValueError("Registry Failed Validation", failures)
        else:
            logging.warning("Registry Failed Validation: %s", failures)
            return False

##--|

@Mixin(_Registration_m, _Instantiation_m, _Verification_m)
class TrackRegistry(_Registry_d):
    """ Stores and manipulates specs, tasks, and artifacts """


    def get_status(self, task:Concrete[TaskName|TaskArtifact]) -> TaskStatus_e|ArtifactStatus_e:
        """ Get the status of a task or artifact """
        match task:
            case TaskArtifact():
                return task.get_status()
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
                logging.info("[%s] %s -> %s", task.name[:], self.get_status(task.name), status) # type: ignore
                self.tasks[task.name].status = status # type: ignore
            case TaskName() as task, TaskStatus_e() if task in self.tasks:
                logging.info("[%s] %s -> %s", task[:], self.get_status(task), status)
                self.tasks[task].status = status
            case TaskName() as task, TaskStatus_e():
                logging.debug("[%s] Not Started Yet", task)
                return False
            case TaskArtifact() as art, ArtifactStatus_e() as stat:
                raise DeprecationWarning("Setting an artifact status is unneeded")
            case _, _:
                raise doot.errors.TrackingError("Bad task update status args", target, status)

        return True

    def get_priority(self, target:Concrete[TaskName|TaskArtifact]) -> int:
        match target:
            case TaskName() if target in self.tasks:
                return self.tasks[target].priority
            case _:
                return API.DECLARE_PRIORITY
