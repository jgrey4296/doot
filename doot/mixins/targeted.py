#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import doot

maybe_build_path = lambda x: pl.Path(x) if x is not None else None

class TargetedMixin:
    """
    For Quickly making a task have cli args to control batching
    """

    def target_params(self) -> list:
        return [
            {"name": "target", "short": "t", "type": maybe_build_path, "default": None},
            {"name": "all", "long": "all", "type": bool, "default": False},
        ]

    def glob_all(self, rec=None, fn=None, root:pl.Path=None):
        match self.args, root:
            case {'all': False, 'target': None}, None:
                logging.debug("%s : No Target Specified", self.basename)
                globbed = []
            case {'all': True}, None:
                globbed = super().glob_all()
            case _, x if x is not None:
                globbed = [(y.name, y) for y in self.glob_target(x, fn=fn, rec=rec)]
            case {'target': targ}, None if targ.parts[0] == "~":
                globbed = [(y,name, y) for y in self.glob_target(targ.expanduser(), fn=fn, rec=rec)]
            case {'target': targ}, None if targ.is_absolute():
                globbed = [(y,name, y) for y in self.glob_target(targ, fn=fn, rec=rec)]
            case {'target': targ}, None:
                globbed = [(y.name, y) for y in self.glob_target(self.locs.root / targ, fn=fn, rec=rec)]
            case _, _:
                logging.warning("%s : No Recognizable Target Specified", self.basename)
                globbed = []

        if bool(globbed) and not globbed[0][1].exists():
            logging.error("%s : Target Doesn't Exist : %s", self.basename, globbed[0])
            exit(1)

        return globbed
