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

class EnumBuilder_m:

    @classmethod
    def build(cls, val:str) -> Self:
        try:
            match val:
                case str():
                    return cls[val]
                case cls():
                    return val
        except KeyError:
            logging.warning("Can't Create a flag of (%s):%s. Available: %s", cls, val, list(cls.__members__.keys()))

class FlagsBuilder_m:

    @classmethod
    def build(cls, vals:str|list|dict) -> Self:
        match vals:
            case str():
                vals = [vals]
            case list():
                pass
            case dict():
                vals = [x for x,y in vals.items() if bool(y)]

        base = cls.default
        for x in vals:
            try:
                match x:
                    case str():
                        base |= cls[x]
                    case cls():
                        base |= x
            except KeyError:
                logging.warning("Can't create a flag of (%s):%s. Available: %s", cls, x, list(cls.__members__.keys()))

        return base
