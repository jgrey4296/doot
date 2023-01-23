#/usr/bin/env python3
"""
Utility classes for attribute based access to loaded toml data,
simplifying data['blah']['awe']['awg']
to data.blah.awe.awg

Also allows guarded access:
result = data.on_fail('fallback').somewhere.along.this.doesnt.exist()
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

class TomlAccessProxy:
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
            types_str = self._types_str()
            path_str = ".".join(self._path + ['(' + types_str + ')'])
            raise TypeError("Toml Value doesn't match declared Type: ", path_str, self._value, self._types).with_traceback(TraceHelper()[5:10])

    def __call__(self, wrapper:callable=None):
        self._notify()
        wrapper   = wrapper or (lambda x: x)
        return wrapper(self._value[0])

    def __getattr__(self, attr):
        self._path.append(attr)
        return self

    def _notify(self):
        types_str = self._types_str()
        match self._value, self._path:
            case (val,), []:
                return
            case (str() as val,), [*path]:
                path_str = ".".join(path) + f"   =  \"{val}\" # <{types_str}>"
                TomlAccess._defaulted.append(path_str)
                return
            case (bool() as val,), [*path]:
                path_str = ".".join(path) + f"   =  {str(val).lower()} # <{types_str}>"
                TomlAccess._defaulted.append(path_str)
                return
            case (val,), [*path]:
                path_str = ".".join(path) + f"   =  {val} # <{types_str}>"
                TomlAccess._defaulted.append(path_str)
                return
            case val, path:
                raise TypeError("Unexpected Values found: ", val, path)

    def _types_str(self):
        match self._types:
            case UnionType() as targ:
                types_str = repr(targ)
            case type(__name__=targ):
                types_str = targ
            case _ as targ:
                types_str = str(targ)

        return types_str

    def using(self, val):
        return TomlAccessProxy(val, types=self._types, path=self._path)

class TomlAccess:
    """
    Provides access to toml data (TomlAccess.load(apath))
    but as attributes (data.a.path.in.the.data)
    instead of key access (data['a']['path']['in']['the']['data'])

    while also providing typed, guarded access:
    data.on_fail("test", str | int).a.path.that.may.exist()

    while it can then report missing paths:
    data._report() -> ['a.path.that.may.exist.<str|int>']
    """

    _defaulted : ClassVar[list[str]] = []

    @staticmethod
    def load(path) -> self:
        logging.info("Creating TomlAccess for %s", str(path))
        return TomlAccess("<root>", toml.load(path))

    @staticmethod
    def _report() -> list[str]:
        """
        Report the paths using default values
        """
        return TomlAccess._defaulted[:]

    def __init__(self, path, table, fallback=None):
        assert(isinstance(fallback, (NoneType, TomlAccessProxy)))
        path = path if isinstance(path, list) else [path]
        super().__setattr__("__table"    , table)
        super().__setattr__("_path"     , path)
        super().__setattr__("__fallback" , fallback)

    def on_fail(self, val, types=None) -> TomlAccessProxy:
        """
        use a fallback value in an access chain,
        eg: doot.config.on_fail("blah").this.doesnt.exist() -> "blah"

        *without* throwing a TomlAccessError
        """
        path  = getattr(self, "_path")[:]
        table = getattr(self, "__table")
        assert(path == ["<root>"])
        return TomlAccess(path, table, fallback=TomlAccessProxy(val, types=types))

    def keys(self):
        table  = getattr(self, "__table")
        return list(table.keys())

    def get_table(self):
        return getattr(self, "__table")

    def __setattr__(self, attr, value):
        if attr in getattr(self, "__table"):
            raise AttributeError(attr)
        super().__setattr__(attr, value)

    # TODO -> getattribute

    def __getattr__(self, attr) -> TomlAccessProxy | str | list | int | float | bool:
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

    def __call__(self):
        table    = getattr(self, "__table")
        fallback = getattr(self, "__fallback")
        if fallback is None:
            raise TomlAccessError("Calling a TomlAccess only work's when guarded with on_fail")

        return fallback.using(self.keys())()
