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

    def __init__(self, path, table):
        if not isinstance(path, list):
            path = [path]
        object.__setattr__(self, "__table", table)
        object.__setattr__(self, "__path", path)

    def keys(self):
        table  = object.__getattribute__(self, "__table")
        return table.keys()

    def __setattr__(self, attr, value):
        raise TomlAccessError(attr)

    def __getattr__(self, attr):
        new_path   = object.__getattribute__(self, "__path")[:]
        table  = object.__getattribute__(self, "__table")

        result = table.get(attr)
        if result is None and "_" in attr :
            result = object.__getattribute__(self, "__table").get(attr.replace("_", "-"))

        if result is None:
            path_s = ".".join(new_path)
            available = "/".join(self.keys())
            raise TomlAccessError(f"{path_s}.[{attr}] not found, available: {available}")

        if isinstance(result, dict):
            new_path.append(attr)
            return TomlAccessor(new_path, result)

        return result
