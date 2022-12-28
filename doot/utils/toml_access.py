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


class TomlAccessValue:

    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value

    def __getattr__(self, attr):
        return self

class TomlAccess:

    @staticmethod
    def load(path) -> self:
        return TomlAccess("root", toml.load(path))

    def __init__(self, path, table, fallback=None):
        if not isinstance(path, list):
            path = [path]
        object.__setattr__(self, "__table", table)
        object.__setattr__(self, "__path", path)
        object.__setattr__(self, "__fallback", fallback)

    def or_get(self, val) -> TomlAccessValue:
        """
        use a fallback value in an access chain,
        eg: data_toml.or_get("blah").this.doesnt.exist() -> "blah"

        *without* throwing a TomlAccessError
        """
        path  = object.__getattribute__(self, "__path")[:]
        table = object.__getattribute__(self, "__table")
        return TomlAccess(path, table, fallback=val)

    def keys(self):
        table  = object.__getattribute__(self, "__table")
        return table.keys()

    def __setattr__(self, attr, value):
        raise TomlAccessError(attr)

    def __getattr__(self, attr) -> TomlAccessValue | str | list | int | float:
        new_path = object.__getattribute__(self, "__path")[:]
        table    = object.__getattribute__(self, "__table")
        fallback = object.__getattribute__(self, "__fallback")

        result = table.get(attr)
        if result is None and "_" in attr :
            result = object.__getattribute__(self, "__table").get(attr.replace("_", "-"))

        if result is None and fallback is not None:
            return TomlAccessValue(fallback)

        if result is None:
            path_s    = ".".join(new_path)
            available = "/".join(self.keys())
            raise TomlAccessError(f"{path_s}.[{attr}] not found, available: {available}")

        if isinstance(result, dict):
            new_path.append(attr)
            return TomlAccess(new_path, result, fallback=fallback)

        if fallback is not None:
            return TomlAccessValue(result)

        return result
