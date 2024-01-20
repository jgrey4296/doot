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
import more_itertools as mitz
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import doot
import doot.errors
from doot.mixins.job.walker import WalkerMixin

walk_ignores : Final[list] = doot.config.on_fail(['.git', '.DS_Store', "__pycache__"], list).settings.walking.ignores()
walk_halts   : Final[str]  = doot.config.on_fail([".doot_ignore"], list).settings.walking.halts()

class WalkShadowerMixin(WalkerMixin):
    """
        Walk a directory tree,
        but in addition to the subtask keys [`fpath`, `fstem`, `fname`, and `lpath`],
        the key `shadow_path` is added.
        Combining `shadow_path` with `fname` gives a full file path

        raises doot.errors.DootLocationError if the shadowed path is the same as the original

        The config key `shadow_root` is where a shadowed tree will start.
        eg:
        shadow_root : {data}/unpacked

        `shadow_path` is a path built onto the `shadow_root`, of the file's relation to its own walk root.
        eg:
        root        : {data}/packed
        fpath       : {data}/packed/bg2/raw/data/Scripts.bif
        lpath       : bg2/raw/data/Scripts.bif
        shadow_path : {shadow_root}/bg2/raw/data/ -> {data}/unpacked/bg2/raw/data/

        To allow for easy saving of modified files, in a structure that mirrors the source data

        automatically includes `shadow_root` as a clean target

        can use 'sub_task' and 'head_task', or 'sub_actions', 'head_actions'
    """

    def _build_subtask(self, n:int, uname, **kwargs) -> DootTaskSpec:
        return super()._build_subtask(n, uname, **kwargs,
                                      shadow_path=self._shadow_path(kwargs['fpath']))

    def _shadow_path(self, fpath:pl.Path) -> pl.Path:
        shadow_root = doot.locs[self.spec.extra.shadow_root]
        rel_path    = self.rel_path(fpath)
        result      = shadow_root / rel_path
        if result == fpath:
            raise doot.errors.DootLocationError("Shadowed Path is same as original", fpath)

        return result.parent

    @classmethod
    def stub_class(cls, stub):
        stub['shadow_root'].set(type="pl.Path", default="")


class LazyWalkShadowerMixin(WalkShadowerMixin):

    def _build_subs(self) -> Generator[DootTaskSpec]:
        self.total_subtasks = 0
        logging.debug("%s : Building Shadow SubTasks", self.name)
        for i, (uname, fpath) in enumerate(self.walk_all()):
            shadow_loc = self._shadow_path(fpath)

            if shadow_loc.exists() and fpath.stat().st_mtime_ns <= shadow_loc.stat().st_mtime_ns:
                continue

            match self._build_subtask(i, uname,
                                      fpath=fpath,
                                      fstem=fpath.stem,
                                      fname=fpath.name,
                                      lpath=self.rel_path(fpath),
                                      shadow_path=self._shadow_path(fpath)):
                case None:
                    pass
                case DootTaskSpec() as subtask:
                    self.total_subtasks += 1
                    yield subtask
                case _ as subtask:
                    raise TypeError("Unexpected type for subtask: %s", type(subtask))
