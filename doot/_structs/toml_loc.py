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

from doot.enums import LocationMeta
from doot._structs.key import DootKey

@dataclass
class TomlLocation:
    """ A representation of a location specified in toml.
      This is the single point of truth for converting a location specified in toml
      to preserve its metadata.
      eg: if its a file, protected, etc

    in toml, will be:
      {file="..."},
      {protected="..."}

    or for combinations:
      {loc="...", protected=true...}
    """
    key  : str          = field()
    base : pl.Path      = field()
    meta : LocationMeta = field(default=LocationMeta.default)

    @staticmethod
    def build(key:str, data:dict|str, base:pl.Path=None):
        result = None
        match data:
            case str():
                result = TomlLocation(key=key, base=(base or pl.Path(data)))
            case pl.Path():
                result = TomlLocation(key=key, base=(base or data))
            case TomlLocation():
                result = TomlLocation(key=data.key, base=(base or data.base), meta=data.meta)
            case dict() if base is not None:
                meta   = LocationMeta.build({x:y for x,y in data.items() if x != "loc"})
                result = TomlLocation(key=key, base=base, meta=meta)
            case dict() if 'loc'in data:
                meta   = LocationMeta.build({x:y for x,y in data.items() if x != "loc"})
                result = TomlLocation(key=key, base=pl.Path(data['loc']), meta=meta)

        return result

    def check(self, meta:LocationMeta) -> bool:
        return meta in self.meta
