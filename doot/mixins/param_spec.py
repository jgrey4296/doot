#!/usr/bin/env python3
"""



"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
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
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

from jgdv.cli.param_spec import ParamSpec

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging


class ParamSpecMaker_m:

    @staticmethod
    def build_param(**kwargs:Any) -> ParamSpec:
        """ Utility method for easily making paramspecs """
        return ParamSpec.build(kwargs)
