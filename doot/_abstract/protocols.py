#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import abc
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from tomlguard import TomlGuard
from pydantic import BaseModel

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.enums import ActionResponse_e, TaskMeta_f, TaskStatus_e

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class ProtocolModelMeta(type(Protocol), type(BaseModel)):
    """ Use as the metaclass for pydantic models which are explicit Protocol implementers

      eg:

      class Example(BaseModel, ExampleProtocol, metaclass=ProtocolModelMeta):...

    """
    pass

@runtime_checkable
class SpecStruct_p(Protocol):
    """ Base class for specs, for type matching """

    @property
    def params(self) -> dict:
        pass

@runtime_checkable
class ArtifactStruct_p(Protocol):
    """ Base class for artifacts, for type matching """

    def exists(self, *, data=None) -> bool:
        pass

@runtime_checkable
class ParamStruct_p(Protocol):
    """ Base class for CLI param specs, for type matching
    when 'maybe_consume' is given a list of strs,
    and a dictionary,
    it can match on the args,
    and return an updated diction and a list of values it didn't consume

    """

    def maybe_consume(self, args:list[str], data:dict) -> int:
        pass

@runtime_checkable
class TomlStubber_p(Protocol):
    """
      Something that can be turned into toml
    """

    @classmethod
    def class_help(cls) -> str:
        pass

    @classmethod
    def stub_class(cls, stub:StubStruct_p):
        """
        Specialize a StubStruct_p to describe this class
        """
        pass

    def stub_instance(self, stub:StubStruct_p):
        """
          Specialize a StubStruct_p with the settings of this specific instance
        """
        pass

    @property
    def short_doc(self) -> str:
        """ Generate Job Class 1 line help string """
        pass

    @property
    def doc(self) -> list[str]:
        pass

@runtime_checkable
class StubStruct_p(Protocol):
    """ Base class for stubs, for type matching """

    def to_toml(self) -> str:
        pass

@runtime_checkable
class CLIParamProvider_p(Protocol):
    """
      Things that can provide parameter specs for CLI parsing
    """

    @property
    def param_specs(self) -> list[ParamStruct_p]:
        """  make class parameter specs  """
        pass

@runtime_checkable
class UpToDate_p(Protocol):

    def is_stale(self, *, other:Any=None) -> bool:
        """ Query whether the task's artifacts have become stale and need to be rebuilt"""
        pass

@runtime_checkable
class ActionGrouper_p(Protocol):
    """ For things have multiple named groups of actions """

    def get_group(self, name:str) -> None|list:
        pass

@runtime_checkable
class Loader_p(Protocol):
    """ The protocol for something that will load something from the system, a file, etc
    TODO add a type parameter
    """

    def setup(self, extra_config:TomlGuard) -> Self:
        pass

    def load(self) -> TomlGuard:
        pass

@runtime_checkable
class Buildable_p(Protocol):
    """ For things that need building, but don't have a separate factory
    TODO add type parameter
    """

    @staticmethod
    def build(*args) -> Self:
        pass

@runtime_checkable
class Nameable_p(Protocol):
    """ The protocol for structured names """

    def __hash__(self):
        pass

    def __eq__(self, other) -> bool:
        pass

    def __lt__(self, other) -> bool:
        pass

    def __contains__(self, other) -> bool:
        pass

    def head_str(self) -> str:
        pass

    def tail_str(self) -> str:
        pass

@runtime_checkable
class Key_p(Protocol):
    """ The protocol for a Key, something that used in a template system"""

    def __call__(self, **kwargs) -> Any:
        """ curried full expansion """
        pass

    def __format__(self, spec) -> str:
        """ no expansion str formatting """
        pass

    def format(self, fmt, *, spec=None, state=None) -> str:
        """ expansion str formatting """
        pass

    def expand(self, *sources, fallback=Any, max=None, check=None, **kwargs) -> Any:
        """ full controllable expansion """
        # todo: re-add expansion chaining
        pass

    def keys(self) -> list[Key_p]:
        pass

    def _expansion_hook(self, value) -> Any:
        pass

@runtime_checkable
class Location_p(Protocol):
    """ Something which describes a file system location,
    with a possible identifier, and metadata
    """
    key                 : None|str|Key_p
    path                : pl.Path
    meta                : enum.EnumMeta

    @property
    def abstracts(self) -> tuple[bool, bool, bool]:
        pass

    def check(self, data) -> bool:
        pass

    def exists(self) -> bool:
        pass

    def keys(self) -> set[str]:
        pass

@runtime_checkable
class Factory_p(Protocol):
    """
      Factory protocol: {type}.build
    """

    @classmethod
    def make(cls:type[T], *args, **kwargs) -> T:
        pass

@runtime_checkable
class InstantiableSpecification_p(Protocol):
    """ A Specification that can be instantiated further """

    def instantiate_onto(self, data:None|Self) -> Self:
        pass


@runtime_checkable
class Decorator_p(Protocol):

    def __call__(self, fn):
        pass

    def _target_method(self, fn) -> Callable:
        pass

    def _target_fn(self, fn) -> Callable:
        pass

    def _target_class(self, fn:type) -> type:
        pass

    def _is_marked(self, fn) -> bool:
        pass

    def _apply_mark(self, fn) -> Callable:
        pass

    def _update_annotations(self, fn) -> None:
        pass
