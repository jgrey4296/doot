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
                return val.removeprefix(self.prefix).split("=")
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

    def add_value_to(self, data, val) -> bool:
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

@dataclass
class DootStructuredName:
    """ complex names of the form ".".join(group)::".".join(task) """
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
class DootTaskSpec:
    """ The information needed to describe a generic task

    actions : list[ [args] | {ctor, [args]} | {fn, [args]} ]
    """
    name              : DootStructuredName                         = field()
    doc               : list[str]                                  = field(default_factory=list)
    source            : DootStructuredName|str|None                = field(default=None)
    actions           : list[Any]                                  = field(default_factory=list)

    runs_before       : list[DootTaskArtifact|pl.Path|str]         = field(default_factory=list)
    runs_after        : list[DootTaskArtifact|pl.Path|str]         = field(default_factory=list)
    priority          : int                                        = field(default=0)
    tasker_updates    : list[str]                                  = field(default_factory=list)
    ctor_name         : DootStructuredName                         = field(default=None)
    ctor              : type|Callable|None                         = field(default=None)
    # Any additional information:
    version           : str                                        = field(default="0.1")
    print_level       : str                                        = field(default="INFO")
    flags             : TaskFlags                                  = field(default=TaskFlags.TASK)

    extra             : Tomler                                     = field(default_factory=Tomler)


    @staticmethod
    def from_dict(data:dict, *, ctor:type=None, ctor_name=None):
        """ builds a task spec from a raw dict
          able to handle a name:str = "group::task" form,
          able to convert TaskFlag str's into an or'd enum value
          """
        core_keys = list(DootTaskSpec.__dataclass_fields__.keys())
        core_data   = {}
        extra_data  = {}

        for key, val in data.items():
            if key == "extra":
                extra_data.update(dict(val))
            elif key in core_keys:
                core_data[key] = val
            elif key.replace("-", "_") in core_keys:
                core_data[key.replace("-", "_")] = val
            elif key not in ['name', 'group']:
                extra_data[key] = val

        match data:
            case {"group": group, "name": str() as name}:
                core_data['name']  = DootStructuredName(data['group'], data['name'])
            case {"name": str() as name}:
                core_data['name'] = DootStructuredName.from_str(name)
            case {"name": DootStructuredName() as name}:
                core_data['name'] = name
            case _:
                core_data['name'] = DootStructuredName(None, None)

        if 'flags' in data and any(x not in TaskFlagNames for x in data.get('flags', [])):
            logging.warning("Unknown Task Flag used, check the spec for %s in %s", core_data['name'], data.get('source', ''))

        core_data['flags'] = ftz.reduce(lambda x,y: x|y, map(lambda x: TaskFlags[x],  filter(lambda x: x in TaskFlagNames, core_data.get('flags', ["TASK"]))))

        core_data['ctor']  = ctor or core_data.get('ctor', None)
        if ctor_name is not None:
            core_data['ctor_name']      = DootStructuredName.from_str(ctor_name, form=StructuredNameEnum.CLASS)
        elif ctor is not None:
            core_data['ctor_name']      = DootStructuredName(ctor.__module__, ctor.__name__, form=StructuredNameEnum.CLASS)
        else:
            core_data['ctor_name']      = DootStructuredName.from_str(doot.constants.DEFAULT_PLUGINS['tasker'][0][1], form=StructuredNameEnum.CLASS)

        return DootTaskSpec(**core_data, extra=Tomler(extra_data))


    def specialize_from(self, data:DootTaskSpec) -> DootTaskSpec:
        specialized = {}
        for field in DootTaskSpec.__annotations__.keys():
            match field:
                case "name":
                    specialized[field] = data.name
                case _:
                    default_val = DootTaskSpec.__dataclass_fields__.get(field, None)
                    value = getattr(data, field)
                    if value == default_val or ((not isinstance(value, bool)) and (not bool(value))):
                        value = getattr(self, field)

                    specialized[field] = value

        return DootTaskSpec(**specialized)


    def __hash__(self):
        return hash(str(self.name))

@dataclass
class DootTaskArtifact:
    """ Describes an artifact a task can produce or consume.
    Artifacts can be Definite (concrete path) or indefinite (glob path)
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
    "Stub Task Spec for description in toml"
    ctor       : str|type                     = field(default="doot.task.base_tasker::DootTasker")
    parts      : dict[str, TaskStubPart]      = field(default_factory=dict, kw_only=True)

    # Don't copy these from DootTaskSpec blindly
    skip_parts : ClassVar[set[str]]          = set(["name", "extra", "ctor", "ctor_name", "source", "version"])

    def __post_init__(self):
        self['name'].default     = DootStructuredName.from_str(doot.constants.DEFAULT_STUB_TASK_NAME)
        self['version'].default = "0.1"
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
        else:
            parts.append(TaskStubPart("ctor", type="type", default=f"\"{self.ctor.__module__}::{self.ctor.__name__}\""))

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
    "Describes a single part of a stub task in toml"
    key     : str      = field()
    type    : str      = field(default="str")
    default : Any      = field(default="")
    comment : str      = field(default="")

    def __str__(self) -> str:
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
            case str() if self.type == "type":
                val_str = self.default
            case list() if "Flags" in self.type:
                parts = ", ".join([f"\"{x}\"" for x in self.default])
                val_str = f"[{parts}]"
            case list():
                def_str = ", ".join(str(x) for x in self.default)
                val_str = f"[{def_str}]"
            case dict():
                val_str = f"{{{self.default}}}"
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

        return f"{key_str} = {val_str:<20} # {type_str:<20} {comment_str}"

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
