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
import doot
import doot.errors
from doot._structs.structured_name import DootStructuredName

@dataclass(eq=False, slots=True)
class DootCodeReference(DootStructuredName):
    """
      A reference to a class or function. can be created from a string (so can be used from toml),
      or from the actual object (from in python)
    """
    separator : str                              = field(default=doot.constants.patterns.IMPORT_SEP, kw_only=True)
    _mixins   : list[DootCodeReference]          = field(default_factory=list, kw_only=True)
    _type     : None|type                        = field(default=None, kw_only=True)

    @classmethod
    def from_str(cls, name:str):
        if doot.constants.patterns.TASK_SEP in name:
            raise doot.errors.DootError("Code References should use a single colon, not double")

        if ":" in name:
            try:
                groupHead_r, taskHead_r = name.split(":")
                groupHead = groupHead_r.split(".")
                taskHead = taskHead_r.split(".")
            except ValueError:
                raise doot.errors.DootConfigError("Code ref can't be split correctly, ensure its of the form x.y.z:ClassName", name)
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
                    ref = DootCodeReference.from_alias(mix, "mixin", plugins)
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
