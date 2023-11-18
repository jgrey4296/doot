#!/usr/bin/env python3
"""

"""

##-- builtin imports
from __future__ import annotations

# import abc
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
# from copy import deepcopy
from dataclasses import InitVar, dataclass, field, _MISSING_TYPE
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
# from bs4 import BeautifulSoup
# import construct as C
# import dirty-equals as deq
# import graphviz
# import matplotlib.pyplot as plt
import more_itertools as mitz
# import networkx as nx
# import numpy as np
# import pandas
# import pomegranate as pom
# import pony import orm
# import pronouncing
# import pyparsing as pp
# import rich
# import seaborn as sns
# import sklearn
# import spacy # nlp = spacy.load("en_core_web_sm")
# import stackprinter # stackprinter.set_excepthook(style='darkbg2')
# import sty
# import sympy
# import tomllib
# import toolz
# import tqdm
# import validators
# import z3
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import importlib
from tomler import Tomler
import doot.errors
import doot.constants
from doot.enums import TaskFlags, ReportEnum, StructuredNameEnum

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskFlags]

@dataclass
class DootParamSpec:
    """ Describes a command line parameter to use in the parser
      When `positional`, will not match against a string starting with `prefix`
      consumed in doot._abstract.parser.ArgParser_i's
      produced using doot._abstract.parser.ParamSpecMaker_m classes,
      like tasks, and taskers
    """
    name        : str      = field()
    type        : type     = field(default=bool)

    prefix      : str      = field(default="-")

    default     : Any      = field(default=False)
    desc        : str      = field(default="An undescribed parameter")
    constraints : list     = field(default_factory=list)
    invisible   : bool     = field(default=False)
    positional  : bool     = field(default=False)
    _short       : None|str = field(default=None)

    _repeatable_types : ClassVar[list[Any]] = [list, int]

    separator   : str      = field(default="=")

    @classmethod
    def from_dict(cls, data:dict) -> DootParamSpec:
        return cls(**data)

    @staticmethod
    def key_func(x):
        return (x.positional, x.prefix)

    @property
    def short(self):
        if self.positional:
            return self.name

        if self._short:
            return self._short

        return self.name[0]

    @property
    def inverse(self):
        return f"no-{self.name}"

    @property
    def repeatable(self):
        return self.type in DootParamSpec._repeatable_types and not self.positional

    def _split_name_from_value(self, val):
        match self.positional:
            case False:
                return val.removeprefix(self.prefix).split(self.separator)
            case True:
                return (self.name, val)

    def __eq__(self, val) -> bool:
        match val, self.positional:
            case DootParamSpec(), _:
                return val is self
            case str(), False:
                [head, *_] = self._split_name_from_value(val)
                return head in [self.name, self.short, self.inverse]
            case str(), True:
                return not val.startswith(self.prefix)
            case _, _:
                return False

    def __str__(self):
        if self.invisible:
            return ""

        if self.positional:
            parts = [self.name]
        else:
            parts = [f"{self.prefix}[{self.name[0]}]{self.name[1:]}"]

        parts.append(" " * (PAD-len(parts[0])))
        match self.type:
            case type() if self.type == bool:
                parts.append(f"{'(bool)': <10}:")
            case str() if bool(self.default):
                parts.append(f"{'(str)': <10}:")
            case str():
                parts.append(f"{'(str)': <10}:")
            case _:
                pass

        parts.append(f"{self.desc:<30}")
        pad = " "*max(0, (85 - (len(parts)+sum(map(len, parts)))))
        match self.default:
            case None:
                pass
            case str():
                parts.append(f'{pad}: Defaults to: "{self.default}"')
            case _:
                parts.append(f"{pad}: Defaults to: {self.default}")

        if self.constraints:
            parts.append(": Constrained to: {self.constraints}")
        return " ".join(parts)

    def __repr__(self):
        if self.positional:
            return f"<ParamSpec: {self.name}>"
        return f"<ParamSpec: {self.prefix}{self.name}>"

    def add_value_to(self, data:dict, val:str) -> bool:
        """ if the given value is suitable, add it into the given data """
        [head, *rest] = self._split_name_from_value(val)
        logging.debug("Matching: %s : %s : %s", self.type.__name__, head, rest)
        match self.type.__name__:
            ##-- handle bools and inversion
            case "bool" if bool(rest):
                raise doot.errors.DootParseError("Bool Arguments shouldn't have values: %s : %s", self.name, val)
            case "bool" if head == self.inverse:
                data[self.name] = False
            case "bool":
                data[self.name] = True
            ##-- end handle bools and inversion
            case _ if not bool(rest):
                raise doot.errors.DootParseError("Non-Bool Arguments should have values: %s : %s", self.name, val)
            case "list":
                if self.name not in data:
                    data[self.name] = []
                data[self.name] += rest[0].split(",")
            case "set":
                if self.name not in data:
                    data[self.name] = set()
                data[self.name].update(rest[0].split(","))
            case _ if data.get(self.name, self.default) != self.default:
                raise doot.errors.DootParseError("Trying to re-set an arg already set: %s : %s", self.name, val)
            case _ if len(rest) == 1:
                data[self.name] = self.type(rest[0])
            case _:
                raise doot.errors.DootParseError("Can't understand value: %s : %s", self.name, val)

        return data[self.name] != self.default



    def maybe_consume(self, args:list[str], data:dict) -> bool:
        """
          Given a list of args, possibly add a value to the data.
          operates in place.
          return True if consumed a value

          handles ["--arg=val"], ["-a", "val"], and, if positional, ["val"]
        """
        if not bool(args) or data is None:
            return False
        if args[0] != self:
            return False

        pop_count = 1
        focus     = args[0]
        prefixed  = focus.startswith(self.prefix)
        is_joint  = self.separator in focus
        key, val  = None, None


        match prefixed, is_joint:
            case True, True: # --key=val
                key, val = focus.split(self.separator)
                key = key.removeprefix(self.prefix)
                pass
            case True, False if self.type.__name__ != "bool" and not bool(args):
                raise doot.errors.DootParseError("key lacks a following value", focus, self.type.__name__)
            case True, False if self.type.__name__ != "bool": # [--key, val]
                key = focus.removeprefix(self.prefix)
                val = args[1]
                pop_count = 2
                pass
            case False, False if self.positional: # [val]
                val = focus
            case _, _: # Nonsense
                key = focus.removeprefix(self.prefix)


        match self.type.__name__:
            ## handle bools and inversion
            case "bool" if val is not None:
                raise doot.errors.DootParseError("Bool Arguments shouldn't have values: %s : %s", self.name, val)
            case "bool" if key == self.inverse:
                data[self.name] = False
            case "bool":
                data[self.name] = True
            case _ if val is None:
                raise doot.errors.DootParseError("Non-Bool Arguments should have values: %s : %s", self.name, val)
            ## lists
            case "list" if not isinstance(data[self.name], list):
                raise doot.errors.DootParseError("List param doesn't have a list entry in data dict", self.name)
            case "list":
                data[self.name] += val.split(",")
            case "set" if not isinstance(data[self.name], set):
                raise doot.errors.DootParseError("Set param doesn't have a set entry in data dict", self.name)
            case "set":
                data[self.name].update(val.split(","))
            case _ if data.get(self.name, self.default) != self.default:
                raise doot.errors.DootParseResetError("Trying to re-set an arg already set: %s : %s", self.name, val)
            case _:
                data[self.name] = self.type(val)


        for x in range(pop_count):
            args.pop(0)

        return True

@dataclass
class DootStructuredName:
    """ A Complex name class for identifying tasks and classes.

      Classes are the standard form using in importlib: doot.structs:DootStucturedName
      Tasks use a double colon to separate group from task name: tasks.globGroup::GlobTask

    """
    group           : list[str]          = field(default_factory=list)
    task            : list[str]          = field(default_factory=list)

    private         : bool               = field(default=False, kw_only=True)
    # maybe: tasker : bool               = field(default=False, kw_only=True) -> add '*' at head or tail

    form            : StructuredNameEnum = field(default=StructuredNameEnum.TASK, kw_only=True)
    task_separator  : ClassVar[str] = doot.constants.TASK_SEP

    class_separator : ClassVar[str] = doot.constants.IMPORT_SEP
    subseparator    : ClassVar[str] = "."

    def __post_init__(self):
        match self.group:
            case ["tasks", x] if x.startswith('"') and x.endswith('"'):
                self.group = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(DootStructuredName.subseparator), x[1:-1]))
            case ["tasks", *xs]:
                self.group = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(DootStructuredName.subseparator), xs))
            case list():
                self.group = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(DootStructuredName.subseparator), self.group))
            case str():
                self.group = self.group.split(DootStructuredName.subseparator)
            case None | []:
                self.group = ["default"]

        match self.task:
            case list():
                self.task = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(DootStructuredName.subseparator), self.task))
            case str():
                self.task = self.task.split(DootStructuredName.subseparator)
            case None | []:
                self.task = ["default"]

    def __str__(self) -> str:
        sep = DootStructuredName.task_separator if self.form is StructuredNameEnum.TASK else DootStructuredName.class_separator
        return "{}{}{}".format(self.group_str(), sep, self.task_str())

    def __hash__(self):
        return hash(str(self))

    def __lt__(self, other) -> bool:
        """ Compare two names, return true if other is a subname of this name
        eg: a.b.c < a.b.c.d
        """
        match other:
            case str():
                other = DootStructuredName.from_str(other)
            case DootStructuredName():
                pass
            case _:
                return False

        for x,y in zip(self.group, other.group):
            if x != y:
                return False

        for x,y in zip(self.task, other.task):
            if x != y:
                return False

        return True

    def __contains__(self, other:str):
        return other in str(self)

    def task_str(self):
        return DootStructuredName.subseparator.join(self.task)

    def group_str(self):
        fmt = "{}"
        match self.form:
            case StructuredNameEnum.TASK if len(self.group) > 1:
                # fmt = "tasks.\"{}\""
                fmt = '"{}"'
            case StructuredNameEnum.TASK:
                # fmt = "tasks.{}"
                fmt = "{}"
            case StructuredNameEnum.CLASS | StructuredNameEnum.CALLABLE:
                fmt = "{}"

        base = DootStructuredName.subseparator.join(self.group)
        return fmt.format(base)

    def subtask(self, *subtasks, subgroups:list[str]|None=None):
        return DootStructuredName(self.group + (subgroups or []),
                                   self.task + list(subtasks),
                                   private=self.private
                                   )


    def root(self):
        if self.form in [StructuredNameEnum.CLASS, StructuredNameEnum.CALLABLE]:
            raise TypeError("Getting the root of a class or callable doesn't make sense")
        return f"{self.group_str()}{DootStructuredName.task_separator}{self.task[0]}"

    @staticmethod
    def from_str(name:str, form:StructuredNameEnum=StructuredNameEnum.TASK):
        sep = DootStructuredName.task_separator if form is StructuredNameEnum.TASK else DootStructuredName.class_separator
        if sep in name:
            groupHead_r, taskHead_r = name.split(sep)
            groupHead = groupHead_r.split(DootStructuredName.subseparator)
            taskHead = taskHead_r.split(DootStructuredName.subseparator)
        else:
            groupHead = None
            taskHead  = name
        return DootStructuredName(groupHead, taskHead, form=form)

    def try_import(self) -> Any:
        try:
            mod = importlib.import_module(self.group_str())
            curr = mod
            for name in self.task:
                curr = getattr(curr, name)

            return curr
        except AttributeError as err:
            raise ImportError("Attempted to import %s but failed", str(self)) from err

@dataclass
class DootActionSpec:
    """
      When an action isn't a full blown class, it gets wrapped in this,
      which passes the action spec to the callable.

      TODO: recogise arg prefixs and convert to correct type.
      eg: path:a/relative/path  -> Path(./a/relative/path)
      path:/usr/bin/python  -> Path(/usr/bin/python)

    """
    do         : None|str                = field(default=None)
    args       : list[Any]               = field(default_factory=list)
    kwargs     : Tomler                  = field(default_factory=Tomler)
    inState    : set[str]                = field(default_factory=set)
    outState   : set[str]                = field(default_factory=set)
    fun        : None|Callable           = field(default=None)

    def __str__(self):
        result = []
        if isinstance(self.do, str):
            result.append(f"do={self.do}")
        elif self.do and hasattr(self.do, '__qualname__'):
            result.append(f"do={self.do.__qualname__}")
        elif self.do:
            result.append(f"do={self.do.__class__.__qualname__}")

        if self.args:
            result.append(f"args={[str(x) for x in self.args]}")
        if self.kwargs:
            result.append(f"kwargs={self.kwargs}")
        if self.inState:
            result.append(f"inState={self.inState}")
        if self.outState:
            result.append(f"outState={self.outState}")

        if self.fun and hasattr(self.fun, '__qualname__'):
            result.append(f"calling={self.fun.__qualname__}")
        elif self.fun:
            result.append(f"calling={self.fun.__class__.__qualname__}")

        return f"<ActionSpec: {' '.join(result)} >"

    def __call__(self, task_state:dict):
        return self.fun(self, task_state)

    def set_function(self, fun:Action_p|Callable):
        """
          Sets the function of the action spec.
          if given a class, the class it built,
          if given a callable, that is used directly.

        """
        # if the function/class has an inState/outState attribute, add those to the spec's fields
        if hasattr(fun, 'inState') and isinstance(getattr(fun, 'inState'), list):
            self.inState.update(getattr(fun, 'inState'))

        if hasattr(fun, 'outState') and isinstance(getattr(fun, 'outState'), list):
            self.outState.update(getattr(fun, 'outState'))

        if isinstance(fun, type):
            self.fun = fun()
        else:
            self.fun = fun

        if not callable(self.fun):
            raise doot.errors.DootActionError("Action Spec Given a non-callable fun: %s", fun)

    def verify(self, state:dict, *, fields=None):
        pos = "Output"
        if fields is None:
            pos = "Input"
            fields = self.inState
        if all(x in state for x in fields):
            return

        raise doot.errors.DootActionStateError("%s Fields Missing: %s", pos, [x for x in fields if x not in state])

    def verify_out(self, state:dict):
        self.verify(state, fields=self.outState)

    @staticmethod
    def from_data(data:dict|list, *, fun=None) -> DootActionSpec:
        match data:
            case list():
                action_spec = DootActionSpec(
                    args=data,
                    fun=fun if callable(fun) else None
                    )
                return action_spec

            case dict():
                kwargs = Tomler({x:y for x,y in data.items() if x not in DootActionSpec.__dataclass_fields__.keys()})
                action_spec = DootActionSpec(
                    do=data['do'],
                    args=data.get('args',[]),
                    kwargs=kwargs,
                    inState=set(data.get('inState', set())),
                    outState=set(data.get('outState', set())),
                    fun=fun if callable(fun) else None
                    )
                return action_spec
            case _:
                raise doot.errors.DootActionError("Unrecognized specification data", data)

@dataclass
class DootTaskSpec:
    """ The information needed to describe a generic task

    actions : list[ [args] | {do="", args=[], **kwargs} ]
    """
    name              : DootStructuredName                           = field()
    doc               : list[str]                                    = field(default_factory=list)
    source            : DootStructuredName|str|None                  = field(default=None)
    actions           : list[Any]                                    = field(default_factory=list)

    runs_before       : list[DootTaskArtifact|pl.Path|str]           = field(default_factory=list)
    runs_after        : list[DootTaskArtifact|pl.Path|str]           = field(default_factory=list)
    priority          : int                                          = field(default=0)
    ctor_name         : DootStructuredName                           = field(default=None)
    ctor              : type|Callable|None                           = field(default=None)
    # Any additional information:
    version            : str                                         = field(default="0.1")
    print_levels       : Tomler                                      = field(default_factory=Tomler)
    flags              : TaskFlags                                   = field(default=TaskFlags.TASK)

    extra              : Tomler                                      = field(default_factory=Tomler)

    inject             : list[str]                                   = field(default_factory=list) # For taskers
    @staticmethod
    def from_dict(data:dict, *, ctor:type=None, ctor_name=None):
        """ builds a task spec from a raw dict
          able to handle a name:str = "group::task" form,
          able to convert TaskFlag str's into an or'd enum value
          """
        core_keys = list(DootTaskSpec.__dataclass_fields__.keys())
        core_data   = {}
        extra_data  = {}

        # Integrate extras, normalize keys
        for key, val in data.items():
            match key:
                case "extra":
                    extra_data.update(dict(val))
                case "print_levels":
                    core_data[key] = Tomler(val)
                case x if x in core_keys:
                    core_data[x] = val
                case x if x.replace("-", "_") in core_keys:
                    core_data[x.replace("-", "_")] = val
                case x if x not in ["name", "group"]:
                    extra_data[key] = val

        # Construct group and name
        match data:
            case {"group": group, "name": str() as name}:
                core_data['name']  = DootStructuredName(data['group'], data['name'])
            case {"name": str() as name}:
                core_data['name'] = DootStructuredName.from_str(name)
            case {"name": DootStructuredName() as name}:
                core_data['name'] = name
            case _:
                core_data['name'] = DootStructuredName(None, None)

        # Check flags are valid
        if 'flags' in data and any(x not in TaskFlagNames for x in data.get('flags', [])):
            logging.warning("Unknown Task Flag used, check the spec for %s in %s", core_data['name'], data.get('source', ''))

        core_data['flags'] = ftz.reduce(lambda x,y: x|y, map(lambda x: TaskFlags[x],  filter(lambda x: x in TaskFlagNames, core_data.get('flags', ["TASK"]))))

        # Prepare constructor name
        core_data['ctor']  = ctor or core_data.get('ctor', None)
        if ctor_name is not None:
            core_data['ctor_name']      = DootStructuredName.from_str(ctor_name, form=StructuredNameEnum.CLASS)
        elif ctor is not None:
            core_data['ctor_name']      = DootStructuredName(ctor.__module__, ctor.__name__, form=StructuredNameEnum.CLASS)
        else:
            core_data['ctor_name']      = DootStructuredName.from_str(doot.constants.DEFAULT_PLUGINS['tasker'][0][1], form=StructuredNameEnum.CLASS)

        # prep actions
        core_data['actions'] = [DootActionSpec.from_data(x) for x in core_data.get('actions', [])]

        return DootTaskSpec(**core_data, extra=Tomler(extra_data))

    def specialize_from(self, data:DootTaskSpec) -> DootTaskSpec:
        """
          Specialize an existing task spec, with additional data
        """
        specialized = {}
        for field in DootTaskSpec.__annotations__.keys():
            match field:
                case "name":
                    specialized[field] = data.name
                case "extra":
                   specialized[field] = Tomler.merge(data.extra, self.extra, shadow=True)
                case _:
                    # prefer the newest data, then the unspecialized data, then the default
                    field_data         = DootTaskSpec.__dataclass_fields__.get(field)
                    match getattr(data,field), field_data.default, field_data.default_factory:
                        case x, _MISSING_TYPE(), y if y == Tomler:
                            value = Tomler.merge(getattr(data,field), getattr(self, field), shadow=True)
                        case x, _MISSING_TYPE(), _MISSING_TYPE():
                            value = x or getattr(self, field)
                        case x, y, _MISSING_TYPE() if x == y:
                            value = getattr(self, field)
                        case x, _, _MISSING_TYPE():
                            value = x
                        case x, _MISSING_TYPE(), _ if bool(x):
                            value = x
                        case x, _MISSING_TYPE(), _:
                            value = getattr(self, field)
                        case x, y, z:
                            raise TypeError("Unknown Task Spec Specialization field types", field, x, y, z)

                    specialized[field] = value

        logging.debug("Specialized Task: %s on top of: %s", data.name, self.name)
        return DootTaskSpec(**specialized)

    def __hash__(self):
        return hash(str(self.name))

@dataclass
class DootTaskArtifact:
    """ Describes an artifact a task can produce or consume.
    Artifacts can be Definite (concrete path) or indefinite (glob path)
      TODO: make indefinite pattern paths
    """
    path : pl.Path = field()

    def __hash__(self):
        return hash(self.path)

    def __repr__(self):
        type = "Definite" if self.is_definite else "Indefinite"
        return f"<{type} TaskArtifact: {self.path.name}>"

    def __str__(self):
        return str(self.path)

    def __eq__(self, other:DootTaskArtifact|Any):
        match other:
            case DootTaskArtifact():
                return self.path == other.path
            case _:
                return False

    def __bool__(self):
        return self.exists

    @property
    def exists(self):
        return self.is_definite and self.path.exists()

    @property
    def is_definite(self):
        return self.path.stem not in "*?+"

    @property
    def is_stale(self) -> bool:
        """ whether the artifact itself is stale """
        return False

    def matches(self, other):
        """ match a definite artifact to its indefinite abstraction """
        match other:
            case DootTaskArtifact() if self.is_definite and not other.is_definite:
                parents_match = self.path.parent == other.path.parent
                exts_match    = self.path.suffix == other.path.suffix
                return parents_match and exts_match
            case _:
                raise TypeError(other)

@dataclass
class TaskStub:
    """ Stub Task Spec for description in toml
    Automatically Adds default keys from DootTaskSpec

    This essentially wraps a dict, adding toml stubs parts as you access keys.
    eg:
    obj = TaskStub()
    ob["blah"].type = "int"

    # str(obj) -> will now generate toml, including a "blah" key

    """
    ctor       : str|type                     = field(default="doot.task.base_tasker::DootTasker")
    parts      : dict[str, TaskStubPart]      = field(default_factory=dict, kw_only=True)

    # Don't copy these from DootTaskSpec blindly
    skip_parts : ClassVar[set[str]]          = set(["name", "extra", "ctor", "ctor_name", "source", "version"])

    def __post_init__(self):
        self['name'].default     = DootStructuredName.from_str(doot.constants.DEFAULT_STUB_TASK_NAME)
        self['version'].default  = "0.1"
        # Auto populate the stub with what fields are defined in a TaskSpec:
        for key, type in DootTaskSpec.__annotations__.items():
            if key in TaskStub.skip_parts:
                continue

            self.parts[key] = TaskStubPart(key=key, type=type)

    def to_toml(self) -> str:
        parts = []
        parts.append(self.parts['name'])
        parts.append(self.parts['version'])
        if 'ctor' in self.parts:
            parts.append(self.parts['ctor'])
        elif isinstance(self.ctor, type):
            parts.append(TaskStubPart("ctor", type="type", default=f"\"{self.ctor.__module__}{doot.constants.IMPORT_SEP}{self.ctor.__name__}\""))
        else:
            parts.append(TaskStubPart("ctor", type="type", default=f"\"{self.ctor}\""))

        for key, part in self.parts.items():
            if key in ["name", "version", "ctor"]:
                continue
            parts.append(part)

        return "\n".join(map(str, parts))

    def __getitem__(self, key):
        if key not in self.parts:
            self.parts[key] = TaskStubPart(key)
        return self.parts[key]

    def __iadd__(self, other):
        match other:
            case [head, val] if head in self.parts:
                self.parts[head].default = val
            case [head, val]:
                self.parts[head] = TaskStubPart(head, default=val)
            case { "name" : name, "type": type, "default": default, "doc": doc, }:
                pass
            case { "name" : name, "default": default }:
                pass
            case dict():
                part = TaskStubPart(**other)
            case Tomler():
                pass
            case TaskStubPart() if other.key not in self.parts:
                self.parts[other.key] = other
            case _:
                raise TypeError("Unrecognized Toml Stub component")

@dataclass
class TaskStubPart:
    """ Describes a single part of a stub task in toml """
    key     : str      = field()
    type    : str      = field(default="str")
    prefix  : str      = field(default="")

    default : Any      = field(default="")
    comment : str      = field(default="")

    def __str__(self) -> str:
        """
          the main conversion method of a stub part -> toml string
          the match statement handles the logic of different types.
          eg: lowercasing the python bool from False to false for toml
        """
        # shortcut on being the name:
        if isinstance(self.default, DootStructuredName) and self.key == "name":
            return f"[[tasks.{self.default.group_str()}]]\n{'name':<20} = \"{self.default.task_str()}\""

        key_str     = f"{self.key:<20}"
        type_str    = f"<{self.type}>"
        comment_str = f"{self.comment}"
        val_str     = None

        match self.default:
            case TaskFlags():
                parts = [x.name for x in TaskFlags if x in self.default]
                joined = ", ".join(map(lambda x: f"\"{x}\"", parts))
                val_str = f"[ {joined} ]"
            case "" if self.type == "TaskFlags":
                val_str = f"[ \"{TaskFlags.TASK.name}\" ]"
            case bool():
                val_str = str(self.default).lower()
            case str() if self.type == "type":
                val_str = self.default
            case list() if "Flags" in self.type:
                parts = ", ".join([f"\"{x}\"" for x in self.default])
                val_str = f"[{parts}]"
            case list():
                def_str = ", ".join(str(x) for x in self.default)
                val_str = f"[{def_str}]"
            case dict():
                val_str = "{}"
            case _ if "list" in self.type:
                def_str = ", ".join(str(x) for x in self.default)
                val_str = f"[{def_str}]"
            case _ if "dict" in self.type:
                val_str = f"{{{self.default}}}"
            case int() | float():
                val_str = f"{self.default}"
            case str() if "\n" in self.default:
                flat = self.default.replace("\n", "\\n")
                val_str = f"\"{flat}\""
            case str():
                val_str = f"\"{self.default}\""

        if val_str is None:
            raise TypeError("Unknown stub part reduction:", self)

        return f"{self.prefix}{key_str} = {val_str:<20} # {type_str:<20} {comment_str}"

@dataclass
class DootTraceRecord:
    message : str                      = field()
    flags   : None|ReportEnum          = field()
    args    : list[Any]                = field(default_factory=list)
    time    : datetime.datetime        = field(default_factory=datetime.datetime.now)

    def __str__(self):
        match self.message:
            case str():
                return self.message.format(*self.args)
            case DootTaskSpec():
                return str(self.message.name)
            case _:
                return str(self.message)

    def __contains__(self, other:ReportEnum) -> bool:
        return all([x in self.flags for x in other])

    def __eq__(self, other:ReportEnum) -> bool:
        return self.flags == other

    def some(self, other:reportPositionEnum) -> bool:
        return any([x in self.flags for x in other])
