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
import random

maybe_build_path = lambda x: pl.Path(x) if x is not None else None

target_list_size = doot.config.on_fail(100, int).globbing.target_list()

class TargetedMixin:
    """
    For Quickly making a task have cli args to control batching
    """
    glob_all_as_default = False

    def target_params(self) -> list:
        return [
            {"name": "target", "short": "t", "type": maybe_build_path, "default": None},
            {"name": "all", "long": "all", "type": bool, "default": self.glob_all_as_default},
            {"name": "some", "long": "some", "type": float, "default": -1.0 },
            {"name" : "list", "long": "list", "short": "l", "type": bool, "default": False},
        ]

    def glob_all(self, rec=None, fn=None, root:pl.Path=None) -> Generator[pl.Path]:
        if root is not None:
            yield from ((y.name, y) for y in self.glob_target(x, fn=fn, rec=rec))
            return None

        match self.args:
            case {'list': True}:
                yield from self._list_options()
            case {'target': targ} if bool(targ) and targ.parts[0] == "~":
                yield from ((y.name, y) for y in self.glob_target(targ.expanduser(), fn=fn, rec=rec))
            case {'target': targ} if bool(targ) and targ.is_absolute():
                yield from ((y.name, y) for y in self.glob_target(targ, fn=fn, rec=rec))
            case {'target': targ} if bool(targ):
                yield from ((y.name, y) for y in self.glob_target(self.locs.root / targ, fn=fn, rec=rec))
            case {"some": val} if not val.is_integer() and 0 < val < 1:
                k           = int(len(globbed) * val)
                all_globbed = list(super().glob_all())
                yield from random.choices(all_globbed, k=k)
            case {"some": val} if val.is_integer() and 1 < val:
                all_globbed = list(super().glob_all())
                yield from random.choices(all_globbed, k=int(val))
            case {'all': True}:
                yield from super().glob_all()
            case _:
                logging.warning("%s : No Recognizable Target Specified", self.basename)
                yield from []

    def _list_options(self):
        logging.info("Choices: ")
        choices = [(i,x) for i,x in enumerate(sorted(super().glob_all()))]
        for count, (name, fpath) in choices[:target_list_size]:
            rel_path = self.rel_path(fpath)
            logging.info(f"-- ({count}) {rel_path}")

        selected = input("Choose Zips ids to Unzip: ")
        for i in [int(x) for x in selected.split(" ")]:
            yield choices[i][1]
