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
from dataclasses import InitVar, dataclass, field
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

PAD           : Final[int] = 15
TaskFlagNames : Final[str] = [x.name for x in TaskFlags]

@dataclass(eq=False, slots=True)
class DootStructuredName:
    """ A Complex name class for identifying tasks and classes.

      Classes are the standard form used in importlib: "module.path:ClassName"
      Tasks use a double colon to separate head from tail name: "group.name::TaskName"

    """
    head            : list[str]          = field(default_factory=list)
    tail            : list[str]          = field(default_factory=list)

    separator       : str                = field(default=doot.constants.TASK_SEP, kw_only=True)
    subseparator    : str                = field(default=".", kw_only=True)

    @staticmethod
    def build(name:str|DootStructuredName|type) -> DootStructuredName:
        match name:
            case DootStructuredName():
                return name
            case type():
                return DootCodeReference.from_type(name)
            case str() if doot.constants.TASK_SEP in name:
                return DootTaskName.from_str(name)
            case str() if doot.constants.IMPORT_SEP in name:
                return DootTaskName.from_str(name)
            case _:
                raise doot.errors.DootError("Tried to build a name from a bad value", name)

    def __post_init__(self):
        match self.head:
            case None | []:
                self.head = ["default"]
            case ["tasks", x] if x.startswith('"') and x.endswith('"'):
                self.head = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(self.subseparator), x[1:-1]))
            case ["tasks", *xs]:
                self.head = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(self.subseparator), xs))
            case list():
                self.head = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(self.subseparator), self.head))
            case str():
                self.head = self.head.split(self.subseparator)

        match self.tail:
            case None | []:
                self.tail = ["default"]
            case list():
                self.tail = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(self.subseparator), self.tail))
            case str():
                self.tail = self.tail.split(self.subseparator)

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

        for x,y in zip(self.head, other.head):
            if x != y:
                return False

        for x,y in zip(self.tail, other.tail):
            if x != y:
                return False

        return True

    def __contains__(self, other:str):
        return str(other) in str(self)

    def __eq__(self, other):
        return str(self) == str(other)

    def tail_str(self):
        return self.subseparator.join(self.tail)

    def head_str(self):
        return self.subseparator.join(self.head)

@dataclass(eq=False, slots=True)
class DootCodeReference(DootStructuredName):
    """
      A reference to a class or function. can be created from a string (so can be used from toml),
      or from the actual object (from in python)
    """
    separator : str                              = field(default=doot.constants.IMPORT_SEP, kw_only=True)
    _mixins   : list[DootCodeReference]          = field(default_factory=list, kw_only=True)
    _type     : None|type                        = field(default=None, kw_only=True)

    @classmethod
    def from_str(cls, name:str):
        if doot.constants.TASK_SEP in name:
            raise doot.errors.DootError("Code References should use a single colon, not double")

        if ":" in name:
            groupHead_r, taskHead_r = name.split(":")
            groupHead = groupHead_r.split(".")
            taskHead = taskHead_r.split(".")
        else:
            groupHead = None
            taskHead  = name

        return DootCodeReference(groupHead, taskHead)

    @staticmethod
    def from_type(_type:type):
        groupHead = _type.__module__
        codeHead  = _type.__name__
        ref = DootCodeReference(groupHead, codeHead, _type=_type)
        return ref

    @staticmethod
    def from_alias(alias:str, group:str, plugins:TomlGuard) -> DootCodeReference:
        if group not in plugins:
            return DootCodeReference.from_str(alias)
        match [x for x in plugins[group] if x.name == alias]:
            case [x, *xs]:
                return DootCodeReference.from_str(x.value)
            case _:
                return DootCodeReference.from_str(alias)

    def __str__(self) -> str:
        return "{}{}{}".format(self.module, self.separator, self.value)

    def __repr__(self) -> str:
        code_path = str(self)
        mixins    = ", ".join(str(x) for x in self._mixins)
        return f"<CodeRef: {code_path} Mixins: {mixins}>"

    def __hash__(self):
        return hash(str(self))

    def __iter__(self):
        return iter(self._mixins)

    @property
    def module(self):
        return self.subseparator.join(self.head)

    @property
    def value(self):
        return self.subseparator.join(self.tail)

    def add_mixins(self, *mixins:str|DootCodeReference|type, plugins:TomlGuard=None) -> DootCodeReference:
        to_add = self._mixins[:]
        for mix in mixins:
            match mix:
                case str() if plugins is not None:
                    ref = DootCodeReference.from_alias(mix, "mixins", plugins)
                case str():
                    ref = DootCodeReference.from_str(mix)
                case DootCodeReference():
                    ref = mix
                case type():
                    ref = DootCodeReference.from_type(mix)
                case _:
                    raise TypeError("Unrecognised mixin type", mix)

            if ref not in to_add:
                to_add.append(ref)

        new_ref = DootCodeReference(head=self.head[:], tail=self.tail[:], _mixins=to_add, _type=self._type)
        return new_ref

    def try_import(self, ensure:type=Any) -> Any:
        try:
            if self._type is not None:
                curr = self._type
            else:
                mod = importlib.import_module(self.module)
                curr = mod
                for name in self.tail:
                    curr = getattr(curr, name)

            if bool(self._mixins):
                mixins = []
                for mix in self._mixins:
                    match mix:
                        case DootCodeReference():
                            mixins.append(mix.try_import())
                        case type():
                            mixins.append(mix)
                curr = type(f"DootGenerated:{curr.__name__}", tuple(mixins + [curr]), {})

            if ensure is not Any and not (isinstance(curr, ensure) or issubclass(curr, ensure)):
                raise ImportError("Imported Code Reference is not of correct type", self, ensure)

            return curr
        except ModuleNotFoundError as err:
            raise ImportError("Module can't be found", str(self))
        except AttributeError as err:
            raise ImportError("Attempted to import %s but failed", str(self)) from err

    def to_aliases(self, group:str, plugins:TomlGuard) -> tuple[str, list[str]]:
        base_alias = str(self)
        match [x for x in plugins[group] if x.value == base_alias]:
            case [x, *xs]:
                base_alias = x.name

        if group != "mixins":
            mixins = [x.to_aliases("mixins", plugins)[0] for x in  self._calculate_minimal_mixins(plugins)]
        else:
            mixins = []

        return base_alias, mixins

    def _calculate_minimal_mixins(self, plugins:TomlGuard) -> list[DootCodeReference]:
        found          = set()
        minimal_mixins = []
        for mixin in reversed(sorted(map(lambda x: x.try_import(), self), key=lambda x:  len(x.mro()))):
            if mixin in found:
                continue

            found.update(mixin.mro())
            minimal_mixins.append(mixin)

        return [DootCodeReference.from_type(x) for x in minimal_mixins]

@dataclass(eq=False, slots=True)
class DootTaskName(DootStructuredName):
    """
      A Task Name.
    """

    internal        : bool               = field(default=False, kw_only=True)
    separator       : str                = field(default=doot.constants.TASK_SEP, kw_only=True)
    args            : dict               = field(default_factory=dict)

    @classmethod
    def from_str(cls, name:str, *, args=None):
        if ":" in name:
            groupHead_r, taskHead_r = name.split("::")
            groupHead = groupHead_r.split(".")
            taskHead = taskHead_r.split(".")
        else:
            groupHead = None
            taskHead  = name
        return DootTaskName(groupHead, taskHead, args=args)

    def __post_init__(self):
        match self.head:
            case ["tasks", x] if x.startswith('"') and x.endswith('"'):
                self.head = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(self.subseparator), x[1:-1]))
            case ["tasks", *xs]:
                self.head = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(self.subseparator), xs))
            case list():
                self.head = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(self.subseparator), self.head))
            case str():
                self.head = self.head.split(self.subseparator)
            case None | []:
                self.head = ["default"]

        match self.tail:
            case list():
                self.tail = ftz.reduce(lambda x, y: x + y, map(lambda x: x.split(self.subseparator), self.tail))
            case str():
                self.tail = self.tail.split(self.subseparator)
            case None | []:
                self.tail = ["default"]

        self.internal = self.tail[0].startswith(doot.constants.INTERNAL_TASK_PREFIX) or self.internal

    def __str__(self) -> str:
        return "{}{}{}".format(self.group, self.separator, self.task)

    def __repr__(self) -> str:
        name = str(self)
        return f"<TaskName: {name}>"

    def __hash__(self):
        return hash(str(self))

    @property
    def group(self) -> str:
        fmt = "{}"
        if len(self.head) > 1:
            # fmt = "tasks.\"{}\""
            fmt = '"{}"'
        return fmt.format(self.head_str())

    @property
    def task(self) -> str:
        return self.tail_str()

    def root(self):
        return f"{self.head_str()}{self.separator}{self.tail[0]}"

    def subtask(self, *subtasks, subgroups:list[str]|None=None) -> DootTaskName:
        args = self.args.copy() if self.args else None
        return DootTaskName(self.head + (subgroups or []),
                            self.tail + [str(x) for x in subtasks if x is not None],
                            internal=self.internal,
                            args=args)

    def specialize(self, *, info=None):
        return self.subtask("$specialized$", info, "${}$".format(uuid1().hex))
