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

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
import doot.errors
from doot.enums import ActionResponseEnum, TaskFlags, TaskStatus_e

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@runtime_checkable
class ArtifactStruct_p(Protocol):
    """ Base class for artifacts, for type matching """
    pass

@runtime_checkable
class StubStruct_p(Protocol):
    """ Base class for stubs, for type matching """

    def to_toml(self) -> str:
        pass

@runtime_checkable
class ParamStruct_p(Protocol):
    """ Base class for param specs, for type matching """

    def maybe_consume(self, args:list[str], data:dict) -> int:
        pass

@runtime_checkable
class SpecStruct_p(Protocol):
    """ Base class for specs, for type matching """

    @property
    def params(self) -> dict|TomlGuard:
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
class CLIParamProvider_p(Protocol):
    """
      Things that can provide parameter specs for CLI parsing
    """

    @classmethod
    @property
    def param_specs(cls) -> list[ParamStruct_p]:
        """  make class parameter specs  """
        pass

@runtime_checkable
class UpToDate_p(Protocol):

    def is_stale(self, *, other:Any=None) -> bool:
        """ Query whether the task's artifacts have become stale and need to be rebuilt"""
        pass

@runtime_checkable
class ActionGrouper_p(Protocol):

    def get_group(self, name:str) -> None|list:
        pass

@runtime_checkable
class Loader_p(Protocol):

    def setup(self, extra_config:TomlGuard) -> Self:
        pass

    def load(self) -> TomlGuard:
        pass

@runtime_checkable
class Buildable_p(Protocol):

    @staticmethod
    def build(*args) -> Self:
        pass

@runtime_checkable
class Nameable_p(Protocol):

    def __hash__(self):
        pass

    def __eq__(self, other) -> bool:
        pass

    def __lt__(self, other) -> bool:
        pass

    def __contains__(self, other) -> bool:
        pass

@runtime_checkable
class Key_p(Protocol):

    @property
    def form(self) -> str:
        pass

    @property
    def direct(self) -> str:
        pass

    def redirect(self, spec=None) -> Key_p:
        pass

    def to_path(self, spec=None, state=None, *, chain:list[Key_p]=None, locs:DootLocations=None, on_fail:None|str|pl.Path|Key_p=Any, symlinks:bool=False) -> pl.Path:
        pass

    def within(self, other:str|dict|TomlGuard) -> bool:
        pass

    def expand(self, spec=None, state=None, *, rec=False, insist=False, chain:list[DootKey]=None, on_fail=Any, locs:DootLocations=None, **kwargs) -> str:
        pass

    def to_type(self, spec, state, type_=Any, **kwargs) -> str:
        pass

@runtime_checkable
class Location_p(Protocol):
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
class InstantiableSpecification_p(Protocol):

    def instantiate_onto(self, data:None|Self) -> Self:
        pass

    def make(self):
        pass

@runtime_checkable
class ExecutableTask(Protocol):
    """ Runners pass off to Tasks/Jobs implementing this protocol
      instead of using their default logic
    """

    def setup(self):
        """ """
        pass

    def expand(self) -> list[Task_i|"TaskSpec"]:
        """ For expanding a job into tasks """
        pass

    def execute(self):
        """ For executing a task """
        pass

    def teardown(self):
        """ For Cleaning up the task """
        pass

    def check_entry(self) -> bool:
        """ For signifiying whether to expand/execute this object """
        pass

    def execute_action_group(self, group_name:str) -> "ActRE"|list:
        """ Optional but recommended """
        pass

    def execute_action(self):
        """ For executing a single action """
        pass

    def current_status(self) -> TaskStatus_e:
        pass

    def force_status(self, status:TaskStatus_e):
        pass

    def current_priority(self) -> int:
        pass

    def decrement_priority(self):
        pass
