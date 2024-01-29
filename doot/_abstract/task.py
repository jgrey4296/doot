"""TASKS ARE THE MAIN ABSTRACTIONS MANAGED BY DOOT

  - JOBS create tasks
  - TASKS have actions
  - ACTIONS are individual atomic steps of a task, given the detailed information necessary to perform the step.

Jobs, as they can control refication order, can add setup and teardown tasks.
This can allow interleaving, or grouping.

  Communication:
  Job  -> Task   : by creation
  Task -> Action : by creation
  Action -> Task : by return value, updating task state dict
  Task -> Job    : by reference to the job

  Task -> Task     = Task -> Job -> Task
  Action -> Action = Action -> Task -> Action

"""
from __future__ import annotations

import logging as logmod
import abc
import types
from typing import Generator, NewType, Protocol, Any, runtime_checkable

from tomlguard import TomlGuard
import doot.errors

from doot.enums import TaskFlags, TaskStateEnum, ActionResponseEnum
from doot._abstract.parser import ParamSpecMaker_m
from doot.structs import DootParamSpec, TaskStub, DootTaskSpec, DootTaskName, DootActionSpec


##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@runtime_checkable
class Action_p(Protocol):
    """
    holds individual action information and state, and executes it
    """
    _toml_kwargs : ClassVar[list[str]] = []

    @abc.abstractmethod
    def __call__(self, spec:DootActionSpec, task_state:dict) -> dict|bool|ActionResponseEnum|None:
        raise NotImplementedError()

class TaskBase_i(ParamSpecMaker_m):
    """ Core Interface for Tasks """

    _version         : str       = "0.1"
    _help            : list[str] = []

    @classmethod
    @property
    def param_specs(cls) -> list[DootParamSpec]:
        """  make class parameter specs  """
        return [
            cls.make_param(name="help", default=False, invisible=True, prefix="--"),
            cls.make_param(name="debug", default=False, invisible=True, prefix="--"),
            cls.make_param(name="verbose", default=0, type=int, invisible=True, prefix="--")
           ]

    def __init__(self, spec:DootTaskSpec):
        self.spec       : DootTaskSpec        = spec
        self.status     : TaskStateEnum       = TaskStateEnum.WAIT
        self.flags      : TaskFlags           = TaskFlags.JOB
        self._records   : list[Any]           = []

    @property
    def name(self) -> str:
        return str(self.spec.name)

    @property
    def fullname(self) -> DootTaskName:
        return self.spec.name

    def __hash__(self):
        return hash(self.name)

    def __lt__(self, other:TaskBase_i) -> bool:
        """ Task A < Task B iff A ∈ B.run_after   """
        return (other.name in self.spec.after_artifacts
                or other.name in self.spec.depends_on)

    def __eq__(self, other):
        match other:
            case str():
                return self.name == other
            case TaskBase_i():
                return self.name == other.name
            case _:
                return False

    @property
    def short_doc(self) -> str:
        """ Generate Job Class 1 line help string """
        try:
            split_doc = [x for x in self.__class__.__doc__.split("\n") if bool(x)]
            return ":: " + split_doc[0].strip() if bool(split_doc) else ""
        except AttributeError:
            return ":: "

    @property
    def doc(self) -> list[str]:
        return self.spec.doc or self._help

    @property
    def depends_on(self) -> abc.Generator[str|DootTaskName]:
        for x in self.spec.depends_on:
            yield x

    @property
    def required_for(self) -> abc.Generator[str|DootTaskName]:
        for x in self.spec.required_for:
            yield x

    def add_execution_record(self, arg):
        """ Record some execution record information for display or debugging """
        self._records.append(arg)

    def log(self, msg, level=logmod.DEBUG, prefix=None) -> None:
        """
        utility method to log a message, useful as tasks are running
        """
        prefix : str       = prefix or ""
        lines  : list[str] = []
        match msg:
            case str():
                lines.append(msg)
            case types.LambdaType():
                lines.append(msg())
            case [types.LambdaType()]:
                lines += msg[0]()
            case list():
                lines += msg

        for line in lines:
            logging.log(level, prefix + str(line))

    @classmethod
    @abc.abstractmethod
    def class_help(cls) -> str:
        raise NotImplementedError(cls, "help")

    @classmethod
    @abc.abstractmethod
    def stub_class(cls, TaskStub):
        """
        Specialize a TaskStub to describe this class
        """
        raise NotImplementedError(cls, "stub_class")

    @abc.abstractmethod
    def stub_instance(self, TaskStub):
        """
          Specialize a TaskStub with the settings of this specific instance
        """
        raise NotImplementedError(self.__class__, "stub_instance")

    @property
    @abc.abstractmethod
    def is_stale(self) -> bool:
        """ Query whether the task's artifacts have become stale and need to be rebuilt"""
        raise NotImplementedError()

class Task_i(TaskBase_i):
    """
    holds task information and state, produces actions to execute.

    """

    def __init__(self, spec:DootTaskSpec, *, job:Job_i=None, **kwargs):
        super().__init__(spec)
        self.job     = job
        self.state      = dict(spec.extra)
        self.state.update(kwargs)
        self.state['_task_name']   = self.spec.name
        self.state['_action_step'] = 0

    def __repr__(self):
        return f"<Task: {self.name}>"

    def maybe_more_tasks(self) -> Generator[Task_i]:
        return iter([])

    @classmethod
    def class_help(cls):
        """ Task *class* help. """
        help_lines = [f"Task   : {cls.__qualname__} v{cls._version}", ""]
        mro = " -> ".join(x.__name__ for x in cls.mro())
        help_lines.append(f"Task MRO: {mro}")
        help_lines.append("")
        help_lines += cls._help

        return "\n".join(help_lines)

    @property
    @abc.abstractmethod
    def actions(self) -> Generator[Action_p]:
        """lazy creation of action instances"""
        raise NotImplementedError()

class Job_i(TaskBase_i):
    """
    builds task descriptions, produces no actions
    """

    def __init__(self, spec:DootTaskSpec):
        super().__init__(spec)
        self.args       : dict                 = {}

    @classmethod
    def class_help(cls) -> str:
        """ Job *class* help. """
        help_lines = [f"Job : {cls.__qualname__} v{cls._version}    ({cls.__module__}:{cls.__qualname__})", ""]

        mro = " -> ".join(x.__name__ for x in cls.mro())
        help_lines.append(f"Job MRO: {mro}")
        help_lines.append("")
        help_lines += cls._help

        params = cls.param_specs
        if bool([x for x in params if not x.invisible]):
            help_lines += ["", "Params:"]
            help_lines += [str(x) for x in cls.param_specs if not x.invisible]

        return "\n".join(help_lines)

    @abc.abstractmethod
    def default_task(self, name:str|DootTaskName|None, extra:None|dict|TomlGuard) -> DootTaskSpec:
        raise NotImplementedError(self.__class__, "default_task")

    @abc.abstractmethod
    def specialize_task(self, task:DootTaskSpec) -> DootTaskSpec|None:
        raise NotImplementedError(self.__class__, "specialize_task")

    @abc.abstractmethod
    def build(self, **kwargs) -> abc.Generator[Task_i]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _build_head(self, **kwargs) -> DootTaskSpec:
        raise NotImplementedError()
