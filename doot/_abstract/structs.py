#!/usr/bin/env python3
"""


See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

import abc
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
# from dataclasses import InitVar, dataclass, field
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

import tomlguard

class SpecStruct_p(abc.ABC):
    """ Base class for specs, for type matching """

    @property
    @abc.abstractmethod
    def params(self) -> dict|tomlguard.TomlGuard:
        pass

class ArtifactStruct_p(abc.ABC):
    """ Base class for artifacts, for type matching """
    pass

class StubStruct_p(abc.ABC):
    """ Base class for stubs, for type matching """
    pass
