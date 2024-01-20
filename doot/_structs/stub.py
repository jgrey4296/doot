#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
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
from dataclasses import InitVar, dataclass, field, MISSING
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import importlib
from tomlguard import TomlGuard
import doot.errors
import doot.constants
from doot.enums import TaskFlags, ReportEnum
from doot._structs.sname import DootTaskName, DootCodeReference
from doot._structs.task_spec import DootTaskSpec

PAD           : Final[int]               = 15
TaskFlagNames : Final[str]               = [x.name for x in TaskFlags]
DEFAULT_CTOR  : Final[DootCodeReference] = DootCodeReference.from_str(doot.constants.DEFAULT_PLUGINS['task'][1][1])

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
    ctor       : str|DootCodeReference|type                     = field(default=DEFAULT_CTOR)
    parts      : dict[str, TaskStubPart]                        = field(default_factory=dict, kw_only=True)

    # Don't copy these from DootTaskSpec blindly
    skip_parts : ClassVar[set[str]]          = set(["name", "extra", "ctor", "source", "version"])

    def __post_init__(self):
        self['name'].default     = DootTaskName.from_str(doot.constants.DEFAULT_STUB_TASK_NAME)
        self['version'].default  = "0.1"
        # Auto populate the stub with what fields are defined in a TaskSpec:
        for dcfield in DootTaskSpec.__dataclass_fields__.values():
            if dcfield.name in TaskStub.skip_parts:
                continue
            self.parts[dcfield.name] = TaskStubPart(key=dcfield.name, type=dcfield.type)
            if dcfield.default != MISSING:
                self.parts[dcfield.name].default = dcfield.default

    def to_toml(self) -> str:
        parts = []
        parts.append(self.parts['name'])
        parts.append(self.parts['version'])
        parts.append(self.parts['doc'])
        if 'ctor' in self.parts:
            parts.append(self.parts['ctor'])
        elif isinstance(self.ctor, type):
            parts.append(TaskStubPart("ctor", type="type", default=f"\"{self.ctor.__module__}{doot.constants.IMPORT_SEP}{self.ctor.__name__}\""))
        else:
            parts.append(TaskStubPart("ctor", type="type", default=f"\"{self.ctor}\""))
        if "mixins" in self.parts:
            parts.append(self.parts['mixins'])

        delayed_actions = []
        for key, part in sorted(self.parts.items(), key=lambda x: x[1]):
            if key in ["name", "version", "ctor", "mixins", 'doc']:
                continue
            if 'actions' in key:
                delayed_actions.append(part)
                continue
            parts.append(part)

        # Actions always go at the end
        for part in delayed_actions:
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
            case TomlGuard():
                pass
            case TaskStubPart() if other.key not in self.parts:
                self.parts[other.key] = other
            case _:
                raise TypeError("Unrecognized Toml Stub component")

@dataclass
class TaskStubPart:
    """ Describes a single part of a stub task in toml """
    key      : str      = field()
    type     : str      = field(default="str")
    prefix   : str      = field(default="")

    default  : Any      = field(default="")
    comment  : str      = field(default="")
    priority : int      = field(default=0)

    def __lt__(self, other):
        return self.priority < other.priority

    def __str__(self) -> str:
        """
          the main conversion method of a stub part -> toml string
          the match statement handles the logic of different types.
          eg: lowercasing the python bool from False to false for toml
        """
        # shortcut on being the name:
        if isinstance(self.default, DootTaskName) and self.key == "name":
            return f"[[tasks.{self.default.group}]]\n{'name':<20} = \"{self.default.task}\""

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
            case list() if all(isinstance(x, (int, float)) for x in self.default):
                def_str = ", ".join(str(x) for x in self.default)
                val_str = f"[{def_str}]"
            case list():
                def_str = ", ".join([f'"{x}"' for x in self.default])
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

    def set(self, **kwargs):
        self.type     = kwargs.get('type', self.type)
        self.prefix   = kwargs.get('prefix', self.prefix)
        self.default  = kwargs.get('default', self.default)
        self.comment  = kwargs.get('comment', self.comment)
        self.priority = kwargs.get('priority', self.priority)
