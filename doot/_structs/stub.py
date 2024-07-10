#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
# import abc
import datetime
import enum
import functools as ftz
import importlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
from dataclasses import MISSING, InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, GenericAlias, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
import more_itertools as mitz
from pydantic import (BaseModel, Field, InstanceOf, field_validator,
                      model_validator)
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot._abstract.protocols import (Buildable_p, ProtocolModelMeta,
                                      StubStruct_p)
from doot._structs.code_ref import CodeReference
from doot._structs.task_name import TaskName
from doot._structs.task_spec import TaskSpec
from doot.enums import LocationMeta_f, QueueMeta_e, Report_f, TaskMeta_f

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

TaskFlagNames : Final[str]               = [x.name for x in TaskMeta_f]

DEFAULT_CTOR  : Final[CodeReference] = CodeReference.build(doot.aliases.task[doot.constants.entrypoints.DEFAULT_TASK_CTOR_ALIAS])

class TaskStub(BaseModel, StubStruct_p, Buildable_p, metaclass=ProtocolModelMeta, arbitrary_types_allowed=True):
    """ Stub Task Spec for description in toml
    Automatically Adds default keys from TaskSpec

    This essentially wraps a dict, adding toml stubs parts as you access keys.
    eg:
    obj = TaskStub()
    ob["blah"].type = "int"

    # str(obj) -> will now generate toml, including a "blah" key

    """
    ctor       : str|CodeReference|type                     = DEFAULT_CTOR
    parts      : dict[str, TaskStubPart]                        = {}

    # Don't copy these from TaskSpec blindly
    skip_parts : ClassVar[set[str]]          = set(["name", "extra", "ctor", "source", "version"])

    @classmethod
    def build(cls, data:None|dict=None):
        match data:
            case None:
                return TaskStub()
            case _:
                return TaskStub.model_validate(data)

    @model_validator(mode="after")
    def initial_values(self):
        self['name'].default     = TaskName.build(doot.constants.names.DEFAULT_STUB_TASK_NAME)
        self['version'].default  = "0.1"
        # Auto populate the stub with what fields are defined in a TaskSpec:
        for dcfield, data in TaskSpec.model_fields.items():
            if dcfield in TaskStub.skip_parts:
                continue

            self.parts[dcfield] = TaskStubPart(key=dcfield, type_=data.annotation)
            if data.default_factory is not None:
                self.parts[dcfield].default = data.default_factory()
            else:
                self.parts[dcfield].default= data.default

        return self

    def __getitem__(self, key):
        if key not in self.parts:
            self.parts[key] = TaskStubPart(key=key)
        return self.parts[key]

    def __contains__(self, key):
        return key in self.parts

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
            case TomlGuard():
                pass
            case TaskStubPart() if other.key not in self.parts:
                self.parts[other.key] = other
            case _:
                raise TypeError("Unrecognized Toml Stub component")

    def to_toml(self) -> str:
        parts = []
        parts.append(self.parts['name'])
        parts.append(self.parts['version'])
        parts.append(self.parts['doc'])
        if 'ctor' in self.parts:
            parts.append(self.parts['ctor'])
        elif isinstance(self.ctor, type):
            parts.append(TaskStubPart(key="ctor", type_="type", default=f"\"{self.ctor.__module__}{doot.constants.patterns.IMPORT_SEP}{self.ctor.__name__}\""))
        else:
            parts.append(TaskStubPart(key="ctor", type_="type", default=f"\"{self.ctor}\""))

        delayed_actions = []
        for key, part in sorted(self.parts.items(), key=lambda x: x[1]):
            if key in ["name", "version", "ctor", "doc"]:
                continue
            if 'actions' in key:
                delayed_actions.append(part)
                continue
            parts.append(part)

        # Actions always go at the end
        for part in delayed_actions:
            parts.append(part)

        return "\n".join(map(str, parts))

class TaskStubPart(BaseModel, arbitrary_types_allowed=True):
    """ Describes a single part of a stub task in toml """
    key       : str
    type_     : str|InstanceOf[type]|Any       = "str"
    prefix    : str                            = ""

    default   : Any                            = Field(default="Undefined")
    comment   : str                            = ""
    priority  : int                            = 0

    def __lt__(self, other):
        return self.priority < other.priority

    def __str__(self) -> str:
        """
          the main conversion method of a stub part -> toml string
          the match statement handles the logic of different types.
          eg: lowercasing the python bool from False to false for toml
        """
        # shortcut on being the name:
        if isinstance(self.default, TaskName) and self.key == "name":
            return f"[[tasks.{self.default.group}]]\n{'name':<20} = \"{self.default.task}\""

        key_str     = self._key_str()
        type_str    = self._type_str()
        comment_str = self._comment_str()
        val_str     = self._default_str()

        return f"{self.prefix}{key_str} = {val_str:<20} # {type_str:<20} # {comment_str}"

    def set(self, **kwargs):
        self.type_     = kwargs.get('type_', self.type_)
        self.prefix    = kwargs.get('prefix', self.prefix)
        self.default   = kwargs.get('default', self.default)
        self.comment   = kwargs.get('comment', self.comment)
        self.priority  = kwargs.get('priority', self.priority)

    def _key_str(self) -> str:
        return f"{self.key:<20}"

    def _type_str(self) -> str:
        match type(self.type_), self.type_:
            case x, t if x == GenericAlias and bool(t.__args__) and hasattr(t.__args__[0], "__args__"):
                args = self.type_.__args__[0].__args__
                args_s = " | ".join(arg.__name__ for arg in args)
                return f"<{self.type_.__name__}[{args_s}]>"
            case _, t if hasattr(t, "__name__"):
                return f"<{self.type_.__name__}>"
            case _, _:
                return f"<{self.type_}>"

    def _comment_str(self) -> str:
        return f"{self.comment}"

    def _default_str(self) -> str:
        match self.default:
            case "" if isinstance(self.type_, enum.EnumMeta):
                val_str = f'[ "{self.type_.default.name}" ]'
            case enum.Flag(): # TaskMeta_f() | LocationMeta_f():
                parts = [x.name for x in TaskMeta_f if x in self.default]
                joined = ", ".join(map(lambda x: f"\"{x}\"", parts))
                val_str = f"[ {joined} ]"
            case QueueMeta_e():
                val_str = '"{}"'.format(self.default.name)
            case bool():
                val_str = str(self.default).lower()
            case str() if self.type_ == "type":
                val_str = self.default
            case int() | float():
                val_str = f"{self.default}"
            case str() if "\n" in self.default:
                flat = self.default.replace("\n", "\\n")
                val_str = f'"{flat}"'
            case str():
                val_str = f'"{self.default}"'
            case list() if all(isinstance(x, (int, float)) for x in self.default):

                def_str = ", ".join(str(x) for x in self.default)
                val_str = f"[{def_str}]"
            case list():
                parts = ", ".join([f'"{x}"' for x in self.default])
                val_str = f"[{parts}]"
            case dict() | TomlGuard() if not bool(self.default):
                val_str = "{}"
            case _:
                logging.debug("Unknown stub part reduction: %s : %s : %s", self.key, self.type_, self.default)
                breakpoint()
                pass
                val_str = '"unknown"'

        return val_str
