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
# import more_itertools as mitz
# from boltons import
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from pydantic import BaseModel, Field, model_validator, field_validator, ValidationError
from tomlguard import TomlGuard
import doot
import doot.errors
from doot._structs.task_name import DootTaskName
from doot._structs.code_ref import DootCodeReference
from doot._structs.artifact import DootTaskArtifact
from doot._abstract.structs import SpecStruct_p

class DependencySpec(BaseModel):
    """
    A Means of representating advanced dependencies.
    Doesn't encode the *whole* dependency, just:
    - task, the endpoint, as its only ever used through a parent taskspec,
      which may have been instantiated
    - keys, any *spec* keys which have to match between the two tasks.

    used in toml as:
    depends_on = [{task="some::task", keys=["fpath", "root"]]
    """
    task       : DootTaskName|DootTaskArtifact
    keys       : list[str]                     = []

    @staticmethod
    def build(data:DependencySpec|TomlGuard|dict|DootTaskName|str) -> DependencySpec:
        match data:
            case DependencySpec():
                return data
            case str():
                return DependencySpec(task=DootTaskName.build(data))
            case TomlGuard() | dict():
                return DependencySpec(task=DootTaskName.build(data['task'], keys=data['keys']))
            case _:
                raise ValueError("Bad data used for dependency spec", data)
