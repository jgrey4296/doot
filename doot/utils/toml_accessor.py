#/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

try:
    # For py 3.11 onwards:
    import tomllib as toml
except ImportError:
    # Fallback to external package
    import toml


if TYPE_CHECKING:
    # tc only imports
    pass
##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


class TomlAccessError(AttributeError):
    pass


class TomlAccessor:

    @staticmethod
    def load(path) -> self:
        return TomlAccessor("root", toml.load(path))

    def __init__(self, attr, table):
        object.__setattr__(self, "__table", table)
        object.__setattr__(self, "__path", [attr])

    def keys(self):
        return self.__table.keys()

    def __setattr__(self, attr, value):
        raise TomlAccessError(attr)

    def __getattr__(self, attr):
        result = object.__getattribute__(self, "__table").get(attr)
        path   = object.__getattribute__(self, "__path")
        if result is None:
            raise TomlAccessError(f"{path}.{attr}")

        if isinstance(result, dict):
            return TomlAccessor(f"{path}.{attr}", result)

        return result
