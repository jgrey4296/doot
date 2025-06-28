 #!/usr/bin/env python3
"""

"""
# # mypy: disable-error-code="attr-defined"
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
from doot.workflow import DootTask, TaskArtifact, TaskName
from doot.workflow import _interface as S_API#  noqa: N812
from doot.workflow._interface import (ActionSpec_i, ArtifactStatus_e, RelationMeta_e,
                                      InjectSpec_i, RelationSpec_i, TaskMeta_e,
                                      TaskName_p, TaskSpec_i, TaskStatus_e, Task_p, Artifact_i)
# ##-- end 1st party imports

# ##-| Local
from . import _interface as API # noqa: N812

# # End of Imports.

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
    type ActionElem  = ActionSpec_i|RelationSpec_i
    type ActionGroup = list[ActionElem]
##--|
##
from doot.workflow._interface import Task_i
# isort: on
# ##-- end types

##-- logging
logging          = logmod.getLogger(__name__)
logging.disabled = False
##-- end logging

##--|

class _Registration_m(API.Registry_d):

    def register_spec(self, spec:TaskSpec_i) -> None:
        """ Register task specs, abstract or concrete

        An initial concrete instance will be created for any abstract spec.

        Specs with names ending in $partial$ will apply their direct .sources predecessor
        under themselves, and pop off the 'partial' name
        That predecessor can not be partial itself
        """
        x           : Any
        ##--|
        if TaskMeta_e.DISABLED in spec.meta:
            logging.info("[Disabled] task: %s", spec.name[:])
            return

        match spec.name:
            case TaskName_p() as x if x in self.specs:
                if self.specs[x] is not spec:
                    raise ValueError("Tried to overwrite a spec", spec.name)
                return
            case TaskName_p() as x if TaskName.Marks.partial in x:
                raise ValueError("By this point a partial spec should have been reified", x)
            case TaskName_p() if x.uuid():
                logging.info("[+.Concrete] : %s", spec.name)
                self.concrete[spec.name.de_uniq()].append(spec.name)
            case TaskName_p():
                logging.info("[+.Abstract] : %s", spec.name)
                self._register_blocking_relations(spec)
                self._register_implicit_spec_names(spec)

        self.specs[spec.name] = spec
        self._register_spec_artifacts(spec)


    def _register_spec_artifacts(self, spec:TaskSpec_i) -> None:
        """ Register the artifacts a spec produces """
        assert(hasattr(self._tracker, "_factory"))
        for rel in self._tracker._factory.action_group_elements(spec):
            match rel:
                case RelationSpec_i(target=TaskArtifact() as art, relation=reltype):
                    self._register_artifact(art, spec.name, relation=reltype)
                case _:
                    pass

    def _register_artifact(self, art:Artifact_i, *tasks:TaskName_p, relation:Maybe[S_API.RelationMeta_e]=None) -> None:
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
                self.artifact_consumers[art].update(tasks)
            case S_API.RelationMeta_e.blocks:
                self.artifact_builders[art].update(tasks)

    def _register_blocking_relations(self, spec:TaskSpec_i) -> None:
        """ a Task[required_for=[x,y,z] blocks x,y,z,
        but if you just look at x,y,z, you can't know that.
        This is the reverse mapping to allow for that

        """
        assert(not spec.name.uuid())
        assert(hasattr(self._tracker, "_factory"))
        # Register Indirect dependencies:
        # So if spec blocks target,
        # record that target needs spec
        for rel in self._tracker._factory.action_group_elements(spec):
            match rel:
                case RelationSpec_i(target=TaskName_p()|TaskArtifact() as target, relation=RelationMeta_e.blocks) if spec.name.uuid(): # type: ignore[attr-defined]
                    logging.info("[Requirement]: %s : %s", target, spec.name)
                    rel.object = spec.name
                    self.blockers[target].append(rel)
                case _: # Ignore action specs and non
                    pass
        else:
            return

    def _register_implicit_spec_names(self, spec:TaskSpec_i) -> None:
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

    def _register_late_injection(self, task:TaskName_p, inject:InjectSpec_i, parent:TaskName_p) -> None:
        """ Register an injection to run on task initialisation,
        using the state injection's from its parent
        """
        logging.info("[Injection] Registering: %s <- %s", task, parent)
        assert(task not in self.late_injections), (task, parent)
        assert(parent in self.specs)
        self.late_injections[task] = (inject, parent)

class _Instantiation_m(API.Registry_d):

    def instantiate_spec(self, name:Abstract[TaskName_p], *, force:Maybe[bool]=None, extra:Maybe[dict|ChainGuard]=None) -> Maybe[Concrete[TaskName_p]]:
        """ Convert an Asbtract Spec into a Concrete Spec,
          Reuses a existing concrete spec if possible.

        If force=True, forces a new instance to be made
        if force=False, blocks new instances from being made
        """
        assert(hasattr(self._tracker, "_factory"))
        match force:
            case None|False if name.uuid() and name in self.specs: # Re-use existing instance
                if bool(extra):
                    raise ValueError("tried to instance a spec, while disallowing new specs, but providing extra values")
                return name
            case _:
                pass

        assert(not name.uuid())
        match self.concrete.get(name, []), force:
            case _, True: # disallow reuse
                pass
            case _, None if extra: # extra data provided
                pass
            case [x, *xs], None|False: # reuse
                logging.info("[Instance.Concrete] : %s", x)
                return x

        spec           = self.specs[name]
        instance_spec  = self._tracker._factory.instantiate(spec, extra=extra)
        assert(instance_spec is not None)
        assert(instance_spec.name.uuid())
        logging.debug("[Instance.new] %s into %s", name, instance_spec.name)
        # register the actual concrete spec
        self._tracker.register(instance_spec) # type: ignore[attr-defined]

        assert(instance_spec.name in self.specs)
        return instance_spec.name

    def instantiate_relation(self, rel:RelationSpec_i, *, control:Concrete[TaskName_p]) -> Concrete[TaskName_p]:  # noqa: PLR0912
        """ find a matching relation according to constraints,
            or create a new instance if theres no constraints/no match

        returns the concrete TaskName_p of the instanced target of the relation
        """
        x             : Any
        control_obj   : Task_p|TaskSpec_i
        control_data  : TaskSpec_i
        instance      : Maybe[TaskName_p]
        existing      : TaskName_p
        ##--|
        logging.debug("[Instance.Relation] : %s -> %s -> %s", control, rel.relation.name, rel.target)
        ##--| guards
        if control not in self.specs:
            raise doot.errors.TrackingError("Unknown control used in relation", control, rel)
        if rel.target not in self.specs and rel.target[:,:] not in self.concrete:
            raise doot.errors.TrackingError("Unknown target declared in Constrained Relation", control, rel.target)

        assert(isinstance(rel.target, TaskName_p))
        if rel.target.uuid() and rel.target in self.specs:
            logging.debug("[Instance.Relation.Exists] : %s", rel.target)
            return rel.target
        ##--|
        match self.tasks.get(control, None) or self.specs[control]:
            case Task_p() as x:
                control_obj   = x
                control_data  = x.spec
            case TaskSpec_i() as x:
                control_obj   = x
                control_data  = x
            case x:
                raise TypeError(type(x))
        ##--| reuse
        potentials : list = self.concrete.get(rel.target[:,:], [])[:] # type: ignore[call-overload]
        for existing in potentials:
            if not rel.accepts(control_obj, self.tasks.get(existing, None) or self.specs[existing]): # type: ignore[arg-type]
                continue
            logging.debug("[Instance.Relation.Match] : %s", existing)
            return existing
        else:
            # make a new rel.target instance
            match rel.inject:
                case InjectSpec_i() as inj:
                    pass
                case _:
                    instance = self._tracker._instantiate(rel.target, force=True)
                    assert(instance is not None)
                    logging.debug("[Instance.Relation.Basic] : %s", instance)
                    return instance

            # Early injections applied here, so constrained relations can use them
            match inj.apply_from_spec(control_data):
                case dict() as x if not bool(x):
                    instance  = self._tracker._instantiate(rel.target, force=True)
                case x:
                    instance  = self._tracker._instantiate(rel.target, extra=x)

            assert(instance is not None)
            assert(instance not in potentials), instance
            if instance and not inj.validate(control_obj, self.specs[instance], only_spec=True):
                raise doot.errors.TrackingError("Injection did not succeed", inj.validate_details(control_obj, self.specs[instance], only_spec=True))

            self._register_late_injection(instance, inj, control) # type: ignore[attr-defined]
            logging.debug("[Instance.Relation.Inject] : %s", instance)
            return instance

    def make_task(self, name:Concrete[TaskName_p], *, task_obj:Maybe[Task_i]=None) -> Concrete[TaskName_p]:
        """ Build a Concrete Spec's Task object, then register it
          if a task_obj is provided, store that instead

          return the name of the task
          """
        assert(hasattr(self._tracker, "_factory"))
        task : Task_i
        ##--| guards
        match name, task_obj:
            case TaskName_p() as x, _ if not x.uuid():
                raise doot.errors.TrackingError("Tried to build a task using a non-concrete spec", name)
            case TaskName_p() as x, Task_i() as obj if x not in self.tasks:
                self.tasks[x] = obj
                return x
            case TaskName_p() as x, Task_i() as obj:
                raise doot.errors.TrackingError("Tried to provide a task object for already existing task", name)
            case TaskName_p() as x, _ if x not in self.specs:
                raise doot.errors.TrackingError("Tried to make a task from a non-existent spec name", name)
            case TaskName_p() as x, _ if x in self.tasks:
                return x
            case TaskName_p() as x, _ if x not in self.tasks:
                pass
            case name, _:
                raise doot.errors.TrackingError("Tried to make a task from a not-task name", name, task_obj)

        ##--| build
        logging.debug("[Instance] Task Object: %s", name)
        spec = self.specs[name]
        task = self._tracker._factory.make(spec, ensure=Task_i)
        # Store it
        self.tasks[name] = task
        assert(name in self.tasks)
        assert(name.uuid())
        return name

class _Verification_m(API.Registry_d):

    def verify(self, *, strict:bool=True) -> bool:
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
class TrackRegistry(API.Registry_d):
    """ Stores and manipulates specs, tasks, and artifacts """

    def get_status(self, task:Concrete[TaskName_p|Artifact_i]) -> TaskStatus_e|ArtifactStatus_e:
        """ Get the status of a task or artifact """
        match task:
            case Artifact_i():
                return task.get_status()
            case TaskName_p() if task in self.tasks:
               return self.tasks[task].status
            case TaskName_p() if task in self.specs:
                return TaskStatus_e.DECLARED
            case _:
                return TaskStatus_e.NAMED

    def set_status(self, target:Concrete[TaskName_p|Artifact_i]|Task_i, status:TaskStatus_e|ArtifactStatus_e) -> bool:
        """ update the state of a task in the dependency graph
          Returns True on status update,
          False on no task or artifact to update.
        """
        match target, status:
            case Task_i() as task, TaskStatus_e() if task.name in self.tasks:
                logging.info("[%s] %s -> %s", task.name[:], self.get_status(task.name), status)
                self.tasks[task.name].status = status
            case TaskName_p() as task, TaskStatus_e() if task in self.tasks:
                logging.info("[%s] %s -> %s", task[:], self.get_status(task), status)
                self.tasks[task].status = status
            case TaskName_p() as task, TaskStatus_e():
                logging.debug("[%s] Not Started Yet", task)
                return False
            case TaskArtifact() as art, ArtifactStatus_e() as stat:
                raise DeprecationWarning("Setting an artifact status is unneeded")
            case _, _:
                raise doot.errors.TrackingError("Bad task update status args", target, status)

        return True

    def get_priority(self, target:Concrete[TaskName_p|Artifact_i]) -> int:
        match target:
            case TaskName_p() if target in self.tasks:
                return self.tasks[target].priority
            case _:
                return API.DECLARE_PRIORITY
