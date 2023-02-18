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

batch_size       = doot.config.on_fail(10, int).tool.doot.batch.size()

class TargetedMixin:
    """
    For Quickly making a task have cli args to control batching
    """

    def target_params(self) -> list:
        return [
            {"name": "target", "short": "t", "type": str, "default": None},
            {"name": "all", "long": "all", "type": bool, "default": False},
            {"name": "chunkSize", "long": "chunkSize", "type": int, "default": batch_size},
        ]

    def target_chunks(self, *, root=None, base=None):
        match self.args, root:
            case {'all': True}, None:
                globbed = super(base, self).glob_all()
                chunks  = self.chunk(globbed, self.args['chunkSize'])
                return chunks
            case {'all': True}, _:
                globbed = [(x.name, x) for x in self.glob_target(root)]
                chunks  = self.chunk(globbed, self.args['chunkSize'])
                return chunks
            case {'target': None}, None:
                raise Exception("No Target Specified")
            case {'target': None}, _:
                fpath  = root
            case {'target': targ}, None:
                fpath = self.locs.root / targ
            case _, _:
                raise Exception("No Target Specified")

        if not fpath.exists():
            raise Exception("Target Doesn't Exist")

        globbed = [(x.name, x) for x in self.glob_target(fpath)]
        logging.debug("Generating for: %s", [x[0] for x in globbed])
        chunks  = self.chunk(globbed, self.args['chunkSize'])
        return chunks
