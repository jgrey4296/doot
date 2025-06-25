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
                                      TaskName_p, TaskSpec_i, TaskStatus_e, Task_p)
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

class _Registry_d:
    """
    Data used in the registry

    Invariants:
    - every key in tasks has a matching key in specs.
    - every concrete spec is in concrete under its abstract name
    - every implicit task that hasn't been registered is in implicit, mapped to its declaring spec
    """
    _tracker            : API.TaskTracker_i

    specs               : dict[TaskName_p, TaskSpec_i]
    concrete            : dict[Abstract[TaskName_p], list[Concrete[TaskName_p]]]
    implicit            : dict[Abstract[TaskName_p], TaskName_p]
    tasks               : dict[Concrete[TaskName_p], Task_p]
    artifacts           : dict[TaskArtifact, set[Abstract[TaskName_p]]]
    # Artifact sets
    abstract_artifacts  : set[Abstract[TaskArtifact]]
    concrete_artifacts  : set[Concrete[TaskArtifact]]
    # indirect blocking requirements:
    blockers            : dict[Concrete[TaskName_p|TaskArtifact], list[RelationSpec_i]]
    late_injections     : dict[Concrete[TaskName_p], tuple[InjectSpec_i, TaskName_p]]
    artifact_builders   : dict[TaskArtifact, list[TaskName_p]]
    artifact_consumers  : dict[TaskArtifact, list[TaskName_p]]

    def __init__(self, *, tracker:Maybe[API.TaskTracker_p]=None) -> None:
        self._tracker            = tracker # type: ignore[assignment]
        self.specs               = {}
        self.concrete            = defaultdict(list)
        self.implicit            = {}
        self.tasks               = {}
        self.artifacts           = defaultdict(set)
        self.abstract_artifacts  = set()
        self.concrete_artifacts  = set()
        self.artifact_builders   = defaultdict(list)
        self.artifact_consumers  = defaultdict(list)
        self.blockers            = defaultdict(list)
        self.late_injections     = {}

class _Registration_m(_Registry_d):

    def register_spec(self, *specs:TaskSpec_i) -> None:
        """ Register task specs, abstract or concrete

        An initial concrete instance will be created for any abstract spec.

        Specs with names ending in $partial$ will apply their direct .sources predecessor
        under themselves, and pop off the 'partial' name
        That predecessor can not be partial itself
        """
        x           : Any
        registered  : int
        queue       : list[TaskSpec_i]

        registered  = 0
        queue       = list(specs)
        while bool(queue):
            spec = queue.pop(0)
            if TaskMeta_e.DISABLED in spec.meta:
                logging.info("[Disabled] task: %s", spec.name[:])
                continue

            match spec.name:
                case TaskName_p() as x if x in self.specs:
                    if self.specs[x] is not spec:
                        raise ValueError("Tried to overwrite a spec", spec.name)
                    continue
                case TaskName_p() as x if TaskName.Marks.partial in x:
                    raise ValueError("By this point a partial spec should have been reified", x)
                case TaskName_p() if x.uuid(): # type: ignore
                    logging.info("[+.Concrete] : %s", spec.name)
                case TaskName_p():
                    logging.info("[+.Abstract] : %s", spec.name)

            self.specs[spec.name] = spec
            self._register_spec_artifacts(spec)
            if spec.name.uuid():
                self.concrete[spec.name.de_uniq()].append(spec.name)
                # Only concrete specs generate extra
                raw_data : list[dict] = self._tracker._subfactory.generate_specs(spec)
                queue += [self._tracker._factory.build(x) for x in raw_data]
            else:
                self._register_blocking_relations(spec)
                self._register_implicit_spec_names(spec)

            registered += 1
        else:
            logging.debug("[+] %s new", registered)
            pass

    def _register_spec_artifacts(self, spec:TaskSpec_i) -> None:
        """ Register the artifacts a spec produces """
        for rel in self._tracker._factory.action_group_elements(spec):
            match rel:
                case RelationSpec_i(target=TaskArtifact() as art, relation=reltype):
                    self._register_artifact(art, spec.name, relation=reltype)
                case _:
                    pass

    def _register_artifact(self, art:TaskArtifact, *tasks:TaskName_p, relation:Maybe[S_API.RelationMeta_e]=None) -> None:
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

    def _register_blocking_relations(self, spec:TaskSpec_i) -> None:
        """ a Task[required_for=[x,y,z] blocks x,y,z,
        but if you just look at x,y,z, you can't know that.
        This is the reverse mapping to allow for that

        """
        assert(not spec.name.uuid())

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
        if not bool(inject.from_state):
            return
        assert(task not in self.late_injections), (task, parent)
        assert(parent in self.specs)
        self.late_injections[task] = (inject, parent)

class _Instantiation_m(_Registry_d):

    def instantiate_spec(self, name:Abstract[TaskName_p], *, extra:Maybe[dict|ChainGuard|bool]=None) -> Maybe[Concrete[TaskName_p]]:
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
            case TaskName_p() as x if not x.uuid():
                pass
            case TaskName_p() as x if x in self.specs:
                logging.info("[Instance.Uniq] %s", x)
                return x
            case TaskName_p() as x:
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
        instance_spec = self._tracker._factory.instantiate(spec, extra=extra)
        assert(instance_spec is not None)
        assert(instance_spec.name.uuid())
        logging.debug("[Instance.new] %s into %s", name, instance_spec.name)
        # register the actual concrete spec
        self.register_spec(instance_spec) # type: ignore[attr-defined]

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
        injection     : bool|dict
        ##--|
        logging.debug("[Instance.Relation] : %s -> %s -> %s", control, rel.relation.name, rel.target)
        ##--| guards
        if control not in self.specs:
            raise doot.errors.TrackingError("Unknown control used in relation", control, rel)
        if rel.target not in self.specs and rel.target not in self.concrete:
            raise doot.errors.TrackingError("Unknown target declared in Constrained Relation", control, rel.target)

        assert(isinstance(rel.target, TaskName_p))
        if rel.target.uuid() and rel.target in self.specs:
            logging.debug("[Instance.Relation.Exists] : %s", rel.target)
            return rel.target
        ##--|
        match self.tasks.get(control, None) or self.specs[control]:
            case Task_i() as x:
                control_obj   = cast("Task_p", x)
                control_data  = x.spec
            case TaskSpec_i() as x:
                control_obj   = x
                control_data  = x
            case x:
                raise TypeError(type(x))
        ##--| reuse
        potentials  = self.concrete.get(rel.target, [])
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
                    instance = self.instantiate_spec(rel.target, extra=True)
                    assert(instance is not None)
                    logging.debug("[Instance.Relation.Basic] : %s", instance)
                    return instance


            current = self.concrete.get(rel.target, [])[:]
            match inj.apply_from_spec(control_data):
                case dict() as x if not bool(x):
                    injection = True
                case x:
                    injection = x
            instance  = self.instantiate_spec(rel.target, extra=injection)
            if instance and not inj.validate(control_obj, self.specs[instance], only_spec=True):
                raise doot.errors.TrackingError("Injection did not succeed", inj.validate_details(control_obj, self.specs[instance], only_spec=True))
            assert(instance is not None)
            assert(instance not in current)
            self._register_late_injection(instance, inj, control) # type: ignore[attr-defined]
            logging.debug("[Instance.Relation.Inject] : %s", instance)
            return instance


    def make_task(self, name:Concrete[TaskName_p], *, task_obj:Maybe[Task_i]=None, parent:Maybe[Concrete[TaskName_p]]=None) -> Concrete[TaskName_p]:
        """ Build a Concrete Spec's Task object
          if a task_obj is provided, store that instead

          return the name of the task
          """
        task : Task_i

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

        logging.debug("[Instance] Task Object: %s", name)
        spec = self.specs[name]
        match self.late_injections.get(name, None):
            case None:
                late_inject = None
            case _, TaskName_p() as x if x not in self.tasks:
                raise ValueError("Late Injection source is not a task", str(x))
            case InjectSpec_i() as inj, TaskName_p() as control:
                late_inject = (inj, self.tasks[control])

        match parent:
            case None:
                task = self._tracker._factory.make(spec, ensure=Task_i, inject=late_inject)
            case TaskName_p() as x:
                task = self._tracker._factory.make(spec, ensure=Task_i, inject=late_inject, parent=self.tasks.get(x, None))

        # Store it
        self.tasks[name] = task
        return name

class _Verification_m(_Registry_d):

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
class TrackRegistry(_Registry_d):
    """ Stores and manipulates specs, tasks, and artifacts """

    def get_status(self, task:Concrete[TaskName_p|TaskArtifact]) -> TaskStatus_e|ArtifactStatus_e:
        """ Get the status of a task or artifact """
        match task:
            case TaskArtifact():
                return task.get_status()
            case TaskName_p() if task in self.tasks:
               return self.tasks[task].status
            case TaskName_p() if task in self.specs:
                return TaskStatus_e.DECLARED
            case _:
                return TaskStatus_e.NAMED

    def set_status(self, target:Concrete[TaskName_p|TaskArtifact]|Task_i, status:TaskStatus_e|ArtifactStatus_e) -> bool:
        """ update the state of a task in the dependency graph
          Returns True on status update,
          False on no task or artifact to update.
        """
        match target, status:
            case Task_i() as task, TaskStatus_e() if task.name in self.tasks:
                logging.info("[%s] %s -> %s", task.name[:], self.get_status(task.name), status) # type: ignore
                self.tasks[task.name].status = status # type: ignore
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

    def get_priority(self, target:Concrete[TaskName_p|TaskArtifact]) -> int:
        match target:
            case TaskName_p() if target in self.tasks:
                return self.tasks[target].priority
            case _:
                return API.DECLARE_PRIORITY
