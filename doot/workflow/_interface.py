"""
Tasks are the main abstractions managed by Doot

  - JOBS create tasks
  - TASKS have actions
  - ACTIONS are individual atomic steps of a task, given the detailed information necessary to perform the step.

Jobs, as they can control refication order, can add setup and teardown tasks.
This can allow interleaving, or grouping.

  Communication paths:
  Job  -> Task   : by creation
  Task -> Action : by creation
  Action -> Task : by return value, updating task state dict
  Task -> Job    : by reference to the job

  Task -> Task     = Postboxes
  Action -> Action = Action -> Task State -> Action

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv.structs.strang._interface import Strang_p
from jgdv.structs.locator._interface import Location_p
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Any
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload
# Other:
from jgdv._abstract.protocols.general import SpecStruct_p, Buildable_p

if TYPE_CHECKING:
    from jgdv.structs.chainguard import ChainGuard
    from jgdv.structs.strang import CodeReference
    import pathlib as pl
    from jgdv import Maybe, Func
    from typing import Final
    from typing import ClassVar, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from jgdv.cli._interface import ParamSpec_p
    from jgdv._abstract.protocols.general import StubStruct_p

    from doot.workflow import ActionSpec, TaskName
    type ActionReturn = Maybe[dict|bool|ActionResponse_e]
    type RelationTarget  = TaskName_p|Artifact_i
    type RelationMark    = RelationMeta_e

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

##--| Vars
CLI_K             : Final[str]        = "cli"
DASH_S            : Final[str]        = "-"
DEFAULT_JOB       : Final[str]        = "job"
GROUP_K           : Final[str]        = "group"
META_K            : Final[str]        = "meta"
MUST_INJECT_K     : Final[str]        = "must_inject"
NAME_K            : Final[str]        = "name"
NONE_S            : Final[str]        = "None"
SPECIAL_KEYS      : Final[list[str]]  = [CLI_K, MUST_INJECT_K]
SUFFIX_K          : Final[str]        = "_add_suffix"
USCORE_S          : Final[str]        = "_"
DEFAULT_PRIORITY  : Final[int]        = 10
##--| Enum Protocols:

class Status_ep(Protocol):

    @classmethod
    def default(cls) -> Any: ...

    @classmethod
    def pre_set(cls) -> set: ...

    @classmethod
    def success_set(cls) -> set: ...

    @classmethod
    def fail_set(cls) -> set: ...

##--| Enums

class QueueMeta_e(enum.Enum):
    """ available ways a task can be activated for running
      onRegister/auto     : activates automatically when added to the task network
      reactive            : activates if an adjacent node completes

      default             : activates only if uses queues the task, or its a dependencyOf

    """

    default      = enum.auto()
    onRegister   = enum.auto()  # noqa: N815
    reactive     = enum.auto()
    reactiveFail = enum.auto()  # noqa: N815
    auto         = onRegister

class RelationMeta_e(enum.Enum):
    """
      What types+synonyms of task relation there can be,
      in the form Obj {rel} Y,

      eg: cake dependsOn baking.
      or: baking requirementFor cake.
      or: eatingCake conflictsWith givingCake
    """
    needs            = enum.auto()
    blocks           = enum.auto()
    # excludes         = enum.auto() # noqa: ERA001

    @classmethod
    def default(cls) -> RelationMeta_e:
        return cls.needs

class TaskMeta_e(enum.StrEnum):
    """
      Flags describing properties of a task,
      stored in the Task_p instance itself.
    """

    TASK         = enum.auto()
    JOB          = enum.auto()
    TRANSFORMER  = enum.auto()

    INTERNAL     = enum.auto()
    JOB_HEAD     = enum.auto()
    CONCRETE     = enum.auto()
    DISABLED     = enum.auto()

    EPHEMERAL    = enum.auto()
    IDEMPOTENT   = enum.auto()
    REQ_TEARDOWN = enum.auto()
    REQ_SETUP    = enum.auto()
    IS_TEARDOWN  = enum.auto()
    IS_SETUP     = enum.auto()
    THREAD_SAFE  = enum.auto()
    STATEFUL     = enum.auto()
    STATELESS    = enum.auto()
    VERSIONED    = enum.auto()

    @classmethod
    def default(cls) -> Maybe:
        return cls.TASK

class TaskStatus_e(enum.Enum):
    """
      Enumeration of the different states a task/artifact can be in.
      The state is stored in the task object itself.

      Before a task object hsa been created, the tracker
      provides the status according to what specs exist for the task name.

    """
    # Pre-Task Object Creation statuses:
    NAMED           = enum.auto() # A Name, missing a spec
    DECLARED        = enum.auto() # Abstract Spec Exists

    DEFINED         = enum.auto() # Spec has been instantiated into the dependency network

    # Task Object Exists
    DISABLED        = enum.auto() # Artificial state for if a spec or task has been disabled.
    INIT            = enum.auto() # Task Object has been created.
    WAIT            = enum.auto() # Task is awaiting dependency check and pass
    READY           = enum.auto() # Dependencies are done, ready to execute/expand.
    RUNNING         = enum.auto() # Has been given to the runner, waiting for a status update.
    SKIPPED         = enum.auto() # Runner has signaled the task was skipped.
    HALTED          = enum.auto() # Task has reached minimum priority, timing out.
    FAILED          = enum.auto() # Runner has signaled Failure.
    SUCCESS         = enum.auto() # Runner has signaled success.
    TEARDOWN        = enum.auto() # Task is ready to be killed
    DEAD            = enum.auto() # Task is done.

    @classmethod
    def default(cls) -> TaskStatus_e:
        return cls.NAMED

    @classmethod
    def pre_set(cls) -> set:
        return {cls.NAMED, cls.DECLARED, cls.DEFINED}

    @classmethod
    def success_set(cls) -> set:
        return {cls.SUCCESS, cls.TEARDOWN, cls.DEAD}

    @classmethod
    def fail_set(cls) -> set:
        return {cls.SKIPPED, cls.HALTED, cls.FAILED}

class ArtifactStatus_e(enum.Enum):
    """ States an artifact can be in """
    DECLARED = enum.auto() # doesn't exist or not checked
    STALE    = enum.auto() # Exists, but is old
    TOCLEAN  = enum.auto() # May exist, needs to be deleted
    EXISTS   = enum.auto() # Exists

class ActionResponse_e(enum.Enum):
    """
      Description of how a Action went.
    """

    SUCCEED    = enum.auto()
    FAIL       = enum.auto()
    SKIP       = enum.auto()
    SKIP_GROUP = enum.auto()
    SKIP_TASK  = enum.auto()

    # Aliases
    SUCCESS  = SUCCEED

##--| data

class DelayedSpec:
    __slots__ = ("applied", "base", "inject", "overrides", "target")

    base       : TaskName_p
    target     : TaskName_p
    # For from_spec injection
    inject     : list[InjectSpec_i]
    # injection values applied from the creator
    applied    : dict
    # Raw data applied over source
    overrides  : dict

    def __init__(self, **kwargs:Any) -> None:
        self.base       = kwargs.pop("base")
        self.target     = kwargs.pop("target")
        self.inject     = []
        self.applied    = kwargs.pop("applied", None) or {}
        self.overrides  = kwargs.pop("overrides")
        match kwargs.pop("inject", []):
            case None:
                pass
            case [*xs]:
                self.inject += xs
            case x:
                self.inject.append(x)
        assert(not bool(kwargs))
##--| Spec Interfaces

@runtime_checkable
class ActionSpec_i(Buildable_p, Protocol):
    do         : Maybe[CodeReference]
    args       : list[Any]
    kwargs     : ChainGuard
    fun        : Maybe[Func]

    def __call__(self, *args:Any, **kwargs:Any) -> ActionReturn: ...

@runtime_checkable
class InjectSpec_i(Buildable_p, Protocol):
    from_spec    : dict
    from_state   : dict
    from_target  : dict
    literal      : dict
    with_suffix  : Maybe[str]

    def apply_from_spec(self, parent:dict|TaskSpec_i|Task_p) -> dict: ...

    def apply_from_state(self, parent:dict|Task_p) -> dict: ...

    def apply_literal(self, val:Any) -> dict: ...

    def validate(self, control:Task_p|TaskSpec_i, target:Task_p|TaskSpec_i, *, only_spec:bool=False) -> bool: ...

    def validate_details(self, control:Task_p|TaskSpec_i, target:Task_p|TaskSpec_i, *, only_spec:bool=False) -> dict: ...

@runtime_checkable
class RelationSpec_i(Protocol):

    Marks        : ClassVar[type[enum.Enum]]
    ##--|
    target       : TaskName_p|Artifact_i
    relation     : RelationMeta_e
    object       : Maybe[TaskName_p|Artifact_i]
    constraints  : dict[str, str]
    inject       : Maybe[InjectSpec_i]

    def __contains__(self, query:str|enum.Enum|TaskName_p|Artifact_i) -> bool: ...

    def to_ordered_pair(self, obj:RelationTarget, *, target:Maybe[TaskName_p]=None) -> tuple[Maybe[RelationTarget], Maybe[RelationTarget]]: ...

    def instantiate(self, *, obj:Maybe[RelationTarget]=None, target:Maybe[RelationTarget]=None) -> RelationSpec_i:  ...

    def forward_dir_p(self) -> bool: ...

    def accepts(self, control:Task_i|TaskSpec_i, target:Task_i|TaskSpec_i) -> bool: ...

@runtime_checkable
class TaskSpec_i(Protocol):
    """
    The data spec of a task. is created from TOML data
    """

    # task specific extras to use in state
    _default_ctor     : ClassVar[str]
    # Action Groups that are depended on, rather than are dependencies of, this task:
    _blocking_groups  : ClassVar[tuple[str, ...]]
    Marks             : ClassVar[enum.Enum]

    ##--| Core Instance Data
    name     : TaskName_p
    doc      : Maybe[list[str]]
    sources  : list[Maybe[TaskName_p|pl.Path]]

    ##--| Default Action Groups
    actions       : list[ActionSpec_i]
    required_for  : list[ActionSpec_i|RelationSpec_i]
    depends_on    : list[ActionSpec_i|RelationSpec_i]
    setup         : list[ActionSpec_i|RelationSpec_i]
    cleanup       : list[ActionSpec_i|RelationSpec_i]
    on_fail       : list[ActionSpec_i|RelationSpec_i]

    ##--| Any additional information:
    version          : str
    priority         : int
    ctor             : CodeReference
    queue_behaviour  : QueueMeta_e
    meta             : set[TaskMeta_e]

    @property
    def extra(self) -> ChainGuard: ...

    def param_specs(self) -> list: ...

@runtime_checkable
class Action_p(Protocol):
    """
    holds individual action information and state, and executes it
    """

    def __call__(self, spec:ActionSpec_i, task_state:dict) -> ActionReturn:
        pass

@runtime_checkable
class Artifact_i(Location_p, Protocol):
    priority : int

    @override
    def __contains__(self, other:object) -> bool: ...

    def get_status(self) -> ArtifactStatus_e: ...

    def reify(self, other:pl.Path|Location_p) -> Maybe[Artifact_i]: ...
##--|

@runtime_checkable
class TaskName_p(Strang_p, Protocol):

    def with_head(self) -> Self: ...

    def is_head(self) -> bool: ...

    def with_cleanup(self) -> Self:
        pass

    def is_cleanup(self) -> bool:
        pass

    def pop_generated(self) -> Self: ...

##--| Factory protocols

class TaskFactory_p(Protocol):

    def __init__(self, *, spec_ctor:Maybe[type]=None, task_ctor:Maybe[type]=None, job_ctor:Maybe[type]=None): ...

    def build(self, data:ChainGuard|dict|TaskName_p|str) -> TaskSpec_i: ...

    def instantiate(self, obj:TaskSpec_i, *, extra:Maybe[Mapping|bool]=None) -> TaskSpec_i: ...

    def merge(self, *, bot:dict|TaskSpec_i, top:dict|TaskSpec_i, suffix:Maybe[str|Literal[False]]=None) -> TaskSpec_i: ...

    def make(self, obj:TaskSpec_i, *, ensure:Maybe=None, inject:Maybe[tuple[InjectSpec_i, Task_i]]=None, parent:Maybe[Task_i]=None) -> Task_i:  ...

    def action_group_elements(self, obj:TaskSpec_i) -> Iterable[ActionSpec_i|RelationSpec_i]: ...

@runtime_checkable
class SubTaskFactory_p(Protocol):

    def generate_names(self, obj:TaskSpec_i) -> list[TaskName_p]: ...

    def generate_specs(self, obj:TaskSpec_i|Artifact_i|DelayedSpec) -> list[dict]: ...

##--|

@runtime_checkable
class Task_p(Protocol):

    def __init__(self, spec:TaskSpec_i) -> None: ...

    ##--| dunders

    @override
    def __hash__(self): ...

    def __lt__(self, other:TaskName_p|Task_p) -> bool: ...
    """ Task A < Task B iff A ∈ B.run_after   """

    @override
    def __eq__(self, other:object) -> bool: ...

    ##--| properties

    @property
    def name(self) -> TaskName_p: ...

    @property
    def spec(self) -> TaskSpec_i: ...

    @property
    def status(self) -> TaskStatus_e: ...

    @status.setter
    def status(self, val:TaskStatus_e) -> None: ...

    @property
    def priority(self) -> int: ...

    @priority.setter
    def priority(self, val:int) -> None: ...

    @property
    def internal_state(self) -> dict: ...
    ##--| other

    def log(self, msg:str, level:int=logmod.DEBUG, prefix:Maybe[str]=None) -> None: ...
    """ utility method to log a message, useful as tasks are running """

    def prepare_actions(self) -> None: ...

    def get_action_group(self, group_name:str) -> list[ActionSpec_i]: ...

@runtime_checkable
class Job_p(Task_p, Protocol):
    """
    builds tasks
    """

    def expand_job(self) -> list:
        pass

@runtime_checkable
class Task_i(Task_p, Protocol):
    """
    Meta information for a task
    """
    _default_flags   : ClassVar[set[TaskMeta_e]]

    _version         : str
    _help            : tuple[str, ...]
    doc              : tuple[str, ...]
