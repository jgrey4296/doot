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

        Does *not* handle any taskspec generation logic
        """
        x           : Any
        ##--|
        if TaskMeta_e.DISABLED in spec.meta:
            logging.info("[Disabled] task: %s", spec.name[:])
            return

        match spec.name:
            case TaskName_p() as x if x in self.specs:
                if self.specs[x].spec is not spec:
                    raise ValueError("Tried to overwrite a spec", spec.name)
                return
            case TaskName_p() as x if TaskName.Marks.partial in x:
                raise ValueError("By this point a partial spec should have been reified", x)

            case TaskName_p() as x if (x.is_head() or x.is_cleanup()):
                logging.info("[+.generated] : %s", spec.name)
                if (gen_base:=x.de_uniq()) in self.specs:
                    # an explicitly registered abstract head/cleanup
                    self.specs[gen_base].related.add(spec.name)
                if x.uuid() and (originator:=x.pop_generated()) in self.specs:
                    self.specs[originator].related.add(spec.name)
            case TaskName_p() if x.uuid():
                logging.info("[+.Concrete] : %s", spec.name)
                self.concrete.add(spec.name.de_uniq())
                self.specs[spec.name.de_uniq()].related.add(spec.name)
            case TaskName_p():
                logging.info("[+.Abstract] : %s", spec.name)
                self.abstract.add(spec.name)
                self._register_blocking_relations(spec)
            case x:
                raise TypeError(type(x))

        self.specs[spec.name] = API.SpecMeta_d(spec=spec)
        self._register_spec_artifacts(spec)

    def _register_artifact(self, art:Artifact_i, *tasks:TaskName_p, relation:Maybe[S_API.RelationMeta_e]=None) -> None:
        logging.info("[+] Artifact: %s, %s", art, tasks)
        obj : API.ArtifactMeta_d

        match self.artifacts.get(art, None):
            case API.ArtifactMeta_d() as obj:
                pass
            case None:
                obj = API.ArtifactMeta_d(artifact=art)
                self.artifacts[art] = obj

        # Add it to the relevant abstract/concrete set
        match art.is_concrete():
            case True:
                self.concrete.add(art)
            case False:
                self.abstract.add(art)

        match relation:
            case None:
                pass
            case S_API.RelationMeta_e.needs:
                obj.consumers.update(tasks)
            case S_API.RelationMeta_e.blocks:
                obj.builders.update(tasks)

    def _register_spec_artifacts(self, spec:TaskSpec_i) -> None:
        """ Register the artifacts a spec produces """
        assert(hasattr(self._tracker, "_factory"))
        for rel in self._tracker._factory.action_group_elements(spec):
            match rel:
                case RelationSpec_i(target=Artifact_i() as art, relation=reltype):
                    self._register_artifact(art, spec.name, relation=reltype)
                case _:
                    pass

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
                case RelationSpec_i(target=TaskName_p() as target, relation=RelationMeta_e.blocks) if spec.name.uuid(): # type: ignore[attr-defined]
                    logging.info("[Requirement]: %s : %s", target, spec.name)
                    self.specs[target].blocked_by.add(spec.name)
                case RelationSpec_i(target=Artifact_i() as target, relation=RelationMeta_e.blocks) if spec.name.uuid(): # type: ignore[attr-defined]
                    logging.info("[Requirement]: %s : %s", target, spec.name)
                    self.artifacts[target].blocked_by.add(spec.name)
                case _: # Ignore action specs and non
                    pass
        else:
            return

    def _register_late_injection(self, task:TaskName_p, inject:InjectSpec_i, parent:TaskName_p) -> None:
        """ Register an injection to run on task initialisation,
        using the state injection's from its parent
        """
        logging.info("[Injection] Registering: %s <- %s", task, parent)
        assert(parent in self.specs)
        assert(task in self.specs)
        assert(parent.uuid())
        assert(task.uuid())
        self.specs[task].injection_source = (parent, inject)

class _Instantiation_m(API.Registry_d):

    def instantiate_spec(self, name:Abstract[TaskName_p], *, force:Maybe[bool]=None, extra:Maybe[dict|ChainGuard]=None) -> Maybe[Concrete[TaskName_p]]:
        """ Convert an Asbtract Spec into a Concrete Spec,
          Reuses a existing concrete spec if possible.

        If force=True, forces a new instance to be made
        if force=False, blocks new instances from being made
        """
        meta      : API.SpecMeta_d
        spec      : TaskSpec_i
        instance  : TaskSpec_i
        ##--|
        assert(hasattr(self._tracker, "_factory"))
        match force:
            case None|False if name.uuid() and name in self.specs: # Re-use existing instance
                if bool(extra):
                    raise ValueError("tried to instance a spec, while disallowing new specs, but providing extra values")
                self._instantiate_implicit_tasks(name)
                return name
            case _:
                pass

        assert(not name.uuid()), name
        meta = self.specs[name]
        match list(meta.related), force:
            case _, True: # disallow reuse
                pass
            case _, None if extra: # extra data provided
                pass
            case [x, *xs], None|False: # reuse
                logging.info("[Instance.Concrete] : %s", x)
                self._instantiate_implicit_tasks(x)
                return x

        spec     = meta.spec
        instance = self._tracker._factory.instantiate(spec, extra=extra)
        assert(instance is not None)
        assert(instance.name.uuid())
        logging.debug("[Instance.new] %s into %s", name, instance.name)
        # register the actual concrete spec
        self._tracker.register(instance) # type: ignore[attr-defined]
        assert(instance.name in self.specs)
        assert(instance.name in meta.related)
        self._instantiate_implicit_tasks(instance.name)
        return instance.name

    def instantiate_relation(self, rel:RelationSpec_i, *, control:Concrete[TaskName_p]) -> Concrete[TaskName_p]:  # noqa: PLR0912, PLR0915
        """ find a matching relation according to constraints,
            or create a new instance if theres no constraints/no match

        returns the concrete TaskName_p of the instanced target of the relation
        """
        x             : Any
        control_meta  : API.SpecMeta_d
        control_obj   : Task_p | TaskSpec_i
        target        : TaskName_p
        instance      : Maybe[TaskName_p]
        existing      : TaskName_p
        potentials    : list[TaskName_p]
        ##--|
        logging.debug("[Instance.Relation] : %s -> %s -> %s", control, rel.relation.name, rel.target)
        ##--| guards
        if control not in self.specs:
            raise doot.errors.TrackingError("Unknown control used in relation", control, rel)
        match rel.target:
            case TaskName_p() as targ if targ.uuid() and targ in self.specs:
                logging.debug("[Instance.Relation.Exists] : %s", rel.target)
                return rel.target
            case TaskName_p() as targ if targ in self.specs:
                target = targ
            case TaskName_p() as targ if targ.uuid() and targ.de_uniq() in self.specs:
                target = targ.de_uniq()
            case TaskName_p() as targ if targ.pop(top=False) in self.specs:
                target = cast("TaskName_p", targ.pop())
            case TaskName_p() as target:
                raise doot.errors.TrackingError("Unknown target declared in Constrained Relation", control, target)

        assert(isinstance(target, TaskName_p))
        ##--|
        match self.specs[control]:
            case API.SpecMeta_d(task=Task_i() as _task) as control_meta:
                control_obj  = _task
            case API.SpecMeta_d(spec=_spec) as control_meta:
                control_obj  = _spec
        ##--| reuse
        potentials   = list(self.specs[target].related)
        for existing in potentials:
            match self.specs[existing]:
                case API.SpecMeta_d(task=Task_i() as _task) if not rel.accepts(control_obj, _task):
                    continue
                case API.SpecMeta_d(spec=_spec) if not rel.accepts(control_obj, _spec):
                    continue
                case _:
                    logging.debug("[Instance.Relation.Match] : %s", existing)
                    return existing
        else:
            # make a new rel.target instance
            match rel.inject:
                case InjectSpec_i() as inj:
                    pass
                case _:
                    instance = self._tracker._instantiate(target, force=True)
                    assert(instance is not None)
                    logging.debug("[Instance.Relation.Basic] : %s", instance)
                    return instance

            # Early injections applied here, so constrained relations can use them
            match inj.apply_from_spec(control_obj):
                case dict() as x if not bool(x):
                    instance  = self._tracker._instantiate(target, force=True)
                case x:
                    instance  = self._tracker._instantiate(target, extra=x)

            assert(instance is not None)
            assert(instance not in potentials), instance
            if instance and not inj.validate(control_obj, self.specs[instance].spec, only_spec=True):
                raise doot.errors.TrackingError("Injection did not succeed", inj.validate_details(control_obj, self.specs[instance].spec, only_spec=True))

            self._register_late_injection(instance, inj, control) # type: ignore[attr-defined]
            logging.debug("[Instance.Relation.Inject] : %s", instance)
            return instance

    def make_task(self, name:Concrete[TaskName_p], *, task_obj:Maybe[Task_i]=None) -> Concrete[TaskName_p]:
        """ Build a Concrete Spec's Task object, then register it
          if a task_obj is provided, store that instead

          return the name of the task
          """
        assert(hasattr(self._tracker, "_factory"))
        assert(isinstance(name, TaskName_p))
        task : Task_p
        meta : API.SpecMeta_d
        ##--| guards
        match self.specs[name], task_obj:
            case _, _ if not name.uuid():
                raise doot.errors.TrackingError("Tried to build a task using a non-concrete spec", name)
            case None, _:
                raise doot.errors.TrackingError("Tried to make a task from a non-existent spec name", name)
            case API.SpecMeta_d(task=Task_p()), Task_p() as obj:
                raise doot.errors.TrackingError("Tried to provide a task object for already existing task", name)
            case API.SpecMeta_d(task=TaskStatus_e.DEFINED), Task_p() as obj:
                self.specs[name].task = obj
                return name
            case API.SpecMeta_d(task=Task_p()), None:
                return name
            case API.SpecMeta_d(task=TaskStatus_e()), None:
                logging.debug("[Instance] Task Object: %s", name)
                meta  = self.specs[name]
                task  = self._tracker._factory.make(meta.spec, ensure=Task_i)
                # Store it
                meta.task = task
                return name
            case x:
                raise TypeError(type(x))

    def _instantiate_implicit_tasks(self, name:TaskName_p) -> None:
        spec = self.specs[name].spec
        for data in self._tracker._subfactory.generate_specs(spec): # type: ignore[attr-defined]
            implicit = self._tracker._factory.build(data) # type: ignore[attr-defined]
            if implicit.name not in self.specs:
                self._tracker.register(implicit)
            self._tracker._instantiate(implicit.name)

class _Verification_m(API.Registry_d):

    def verify(self, *, strict:bool=True) -> bool:
        failures = []
        for k in (missing:=self.concrete - self.abstract - self.artifacts.keys()):
            failures.append(f"Abstact Spec {k} is missing")

        # TODO Add more verify heuristics
        if not bool(failures):
            return True
        if strict:
            raise ValueError("Registry Failed Validation", failures)
        else:
            logging.warning("Registry Failed Validation: %s", failures)
            return False

##--|

@Proto(API.Registry_p)
@Mixin(_Registration_m, _Instantiation_m, _Verification_m)
class TrackRegistry(API.Registry_d):
    """ Stores and manipulates specs, tasks, and artifacts """

    def get_status(self, target:Concrete[TaskName_p|Artifact_i]) -> tuple[TaskStatus_e|ArtifactStatus_e, int]:
        """ Get the status of a target or artifact """
        assert(hasattr(self._tracker, "_declare_priority"))
        assert(hasattr(self._tracker, "_root_node"))
        if isinstance(target, Artifact_i):
            return target.get_status(), target.priority

        assert(isinstance(target, TaskName_p))
        match self.specs.get(target, None):
            case None if target == self._tracker._root_node:
                return TaskStatus_e.NAMED, self._tracker._declare_priority
            case None if target.uuid() and target.de_uniq() in self.specs:
                return TaskStatus_e.DECLARED, self._tracker._declare_priority
            case API.SpecMeta_d(task=TaskStatus_e() as status):
                return status, self._tracker._declare_priority
            case API.SpecMeta_d(task=Task_p() as _target):
                return _target.status, _target.priority
            case _:
                return TaskStatus_e.NAMED, self._tracker._declare_priority

    def set_status(self, target:Concrete[TaskName_p|Artifact_i], status:TaskStatus_e|ArtifactStatus_e) -> bool:
        """ update the state of a task in the dependency graph
          Returns True on status update,
          False on no task or artifact to update.
        """
        x         : Any
        instance  : TaskName_p
        ##--|
        logging.debug("[Status.=] : %s : %s", target, status)
        match target:
            case Artifact_i() as x:
                return False
            case TaskName_p() as x:
                instance = x
            case x:
                raise TypeError(type(x))

        assert(isinstance(status, TaskStatus_e))
        match self.specs.get(instance, None):
            case None:
                return False
            case API.SpecMeta_d(task=TaskStatus_e()) as _meta:
                _meta.task = status
                return False
            case API.SpecMeta_d(task=Task_p() as _task):
                _task.status = status
                return True
            case x:
                raise TypeError(type(x))
