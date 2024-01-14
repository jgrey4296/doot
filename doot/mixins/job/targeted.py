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

target_list_size = doot.config.on_fail(100, int).settings.walking.target_size()

class TargetedMixin:
    """
    For Quickly making a task have cli args to control batching
    """
    walk_all_as_default = False

    def target_params(self) -> list:
        return [
            {"name": "target", "short": "t", "type": maybe_build_path, "default": None},
            {"name": "all", "long": "all", "type": bool, "default": self.walk_all_as_default},
            {"name": "some", "long": "some", "type": float, "default": -1.0 },
            {"name" : "list", "long": "list", "short": "l", "type": bool, "default": False},
        ]

    def walk_all(self, rec=None, fn=None, root:pl.Path=None) -> Generator[pl.Path]:
        if root is not None:
            yield from ((y.name, y) for y in self.walk_target(x, fn=fn, rec=rec))
            return None

        match self.args:
            case {'list': True}:
                yield from self._list_options()
            case {'target': targ} if bool(targ) and targ.parts[0] == "~":
                yield from ((y.name, y) for y in self.walk_target(targ.expanduser(), fn=fn, rec=rec))
            case {'target': targ} if bool(targ) and targ.is_absolute():
                yield from ((y.name, y) for y in self.walk_target(targ, fn=fn, rec=rec))
            case {'target': targ} if bool(targ):
                yield from ((y.name, y) for y in self.walk_target(self.locs.root / targ, fn=fn, rec=rec))
            case {"some": val} if not val.is_integer() and 0 < val < 1:
                k           = int(len(globbed) * val)
                all_globbed = list(super().walk_all())
                yield from random.choices(all_globbed, k=k)
            case {"some": val} if val.is_integer() and 1 < val:
                all_globbed = list(super().walk_all())
                yield from random.choices(all_globbed, k=int(val))
            case {'all': True}:
                yield from super().walk_all()
            case _:
                logging.warning("%s : No Recognizable Target Specified", self.basename)
                yield from []

    def _list_options(self):
        logging.info("Choices: ")
        choices = list(enumerate(sorted(super().walk_all())))
        max_len = len(choices)
        current_window = (0, target_list_size)
        to_yield = []
        loop = True
        while loop:
            for count, (name, fpath) in choices[current_window[0]:current_window[1]]:
                rel_path = self.rel_path(fpath)
                logging.info(f"-- ({count}) {rel_path}")

            if current_window[1] < max_len:
                print("There are more choices, type ? to list them")
            print(f"Showing Choices: {current_window[0]} - {current_window[1]} of {max_len}")
            print("Confirm and continue with ! on its own")
            match input("Choose ids by number separated by spaces: ").strip():
                case "!":
                    loop = False
                case "?":
                    current_window = tuple(map(lambda x: x+target_list_size, current_window))
                case "":
                    print("Empty Response, try again, or end with !")
                case _ as selected:
                    to_yield += filter(lambda x: 0 <= x < max_len, map(int, selected.split(" ")))

        print("Selected Options: ", " ".join(map(str, to_yield)))

        for i in to_yield:
            yield choices[i][1]
