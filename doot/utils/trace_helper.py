#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

# import abc
# import datetime
# import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
# from uuid import UUID, uuid1
# from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

class TraceHelper:

    def __init__(self):
        self.frames = []
        self.get_frames()

    def __getitem__(self, val=None):
        match val:
            case None:
                return self.to_tb()
            case slice() | int():
                return self.to_tb(self.frames[val])
            case _:
                raise TypeError("Bad value passed to TraceHelper")

    def get_frames(self):
        """ from https://stackoverflow.com/questions/27138440 """
        tb    = None
        depth = 0
        while True:
            try:
                frame = sys._getframe(depth)
                depth += 1
            except ValueError as exc:
                break

            self.frames.append(frame)

    def to_tb(self, frames=None):
        top = None
        frames = frames or self.frames
        for frame in frames:
            top = types.TracebackType(top, frame,
                                     frame.f_lasti,
                                     frame.f_lineno)
        return top
