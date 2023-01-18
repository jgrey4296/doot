#/usr/bin/env python3
"""
Utility classes for attribute based access to loaded toml data,
simplifying data['blah']['awe']['awg']
to data.blah.awe.awg

Also allows guarded access:
result = data.or_get('fallback').somewhere.along.this.doesnt.exist()
restul equals "fallback" or whatever `exist` is.

"""
##-- imports
from __future__ import annotations

import abc
import logging as logmod
import pathlib as pl
from types import NoneType
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from re import Pattern
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from types import UnionType
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

from doot.utils.trace_helper import TraceHelper

class TomlAccessError(AttributeError):
    pass


class TomlAccessValue:
    """
    A Wrapper for guarded access to toml values.
    you get the value by calling it.
    Until then, it tracks attribute access,
    and reports that to TomlAccess when called.
    It also can type check its value and the value retrieved from the toml data
    """

    def __init__(self, value, types=None, path=None):
        types = types or "Any"
        self._value = (value,)
        self._types = types
        self._path  = path or []

        if self._types != "Any" and not isinstance(value, self._types):
            match self._types:
                case UnionType() as targ:
                    types_str = repr(targ)
                case type(__name__=targ):
                    types_str = targ
                case _ as targ:
                    types_str = str(targ)
            path_str = ".".join(path + ['(' + types_str + ')'])
            raise TypeError("Toml Value doesn't match declared Type: ", path_str, self._value, self._types).with_traceback(TraceHelper()[5:10])

    def __call__(self):
        match self._value, self._path:
            case (val,), []:
                return val
            case (val,), [*path]:
                path_str = ".".join(path + [f"<{self._types}>"])
                TomlAccess.missing_paths.append(path_str)
                return val
            case val, path:
                raise TypeError("Unexpected Values found: ", val, path)

    def __getattr__(self, attr):
        self._path.append(attr)
        return self

    def using(self, val):
        return TomlAccessValue(val, types=self._types, path=self._path)

class TomlAccess:
    """
    Provides access to toml data (TomlAccess.load(apath))
    but as attributes (data.a.path.in.the.data)
    instead of key access (data['a']['path']['in']['the']['data'])

    while also providing typed, guarded access:
    data.or_get("test", str | int).a.path.that.may.exist()

    while it can then report missing paths:
    data._report() -> ['a.path.that.may.exist.<str|int>']
    """

    missing_paths : ClassVar[list[str]] = []

    @staticmethod
    def load(path) -> self:
        logging.info("Creating TomlAccess for %s", str(path))
        return TomlAccess("<root>", toml.load(path))

    def __init__(self, path, table, fallback=None):
        assert(isinstance(fallback, (NoneType, TomlAccessValue)))
        path = path if isinstance(path, list) else [path]
        super().__setattr__("__table"    , table)
        super().__setattr__("_path"     , path)
        super().__setattr__("__fallback" , fallback)

    def or_get(self, val, types=None) -> TomlAccessValue:
        """
        use a fallback value in an access chain,
        eg: doot.config.or_get("blah").this.doesnt.exist() -> "blah"

        *without* throwing a TomlAccessError
        """
        path  = getattr(self, "_path")[:]
        table = getattr(self, "__table")
        assert(path == ["<root>"])
        return TomlAccess(path, table, fallback=TomlAccessValue(val, types=types))

    def keys(self):
        table  = object.__getattribute__(self, "__table")
        return table.keys()

    def _report(self) -> list[str]:
        """
        Report the paths using default values
        """
        return TomlAccess.missing_paths[:]

    def __setattr__(self, attr, value):
        if attr in getattr(self, "__table"):
            raise AttributeError(attr)
        super().__setattr__(attr, value)

    # TODO -> getattribute
    def __getattr__(self, attr) -> TomlAccessValue | str | list | int | float | bool:
        table    = getattr(self, "__table")
        fallback = getattr(self, "__fallback")
        if fallback:
            getattr(fallback, attr)
        match (table.get(attr) or table.get(attr.replace("_", "-"))):
            case None if fallback is not None:
                return fallback
            case None:
                path     = getattr(self, "_path")[:]
                path_s    = ".".join(path)
                available = "/".join(self.keys())
                raise TomlAccessError(f"{path_s}.[{attr}] not found, available: {available}")
            case dict() as result:
                path     = getattr(self, "_path")[:]
                return TomlAccess(path + [attr], result, fallback=fallback)
            case _ as result if fallback is not None:
                # Theres a fallback value, so the result needs to be wrapped so it can be called
                return fallback.using(result)
            case _ as result:
                return result
