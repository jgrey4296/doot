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

import doot
import shutil
from doot.cmds.base_cmd import BaseCommand
from collections import defaultdict

##-- logging
logging = logmod.getLogger(__name__)
printer = doot.subprinter()
##-- end logging

clean_locs = doot.config.on_fail([], list).settings.commands.clean.locs()

class CleanCmd(BaseCommand):
    """
      Runs either a general clean command, or a specific task clean command

    """
    _name      = "clean"
    _help      = [
        "Called with a -t[arget]={task}, will delete locations listed in that task's toml spec'd `clean_targets`",
        "Without a target, will delete locations with the 'clean::' metadata",
        "Locations marked 'protect::' will not be cleaned",
        "Directories will *not* be deleted unless -r[ecursive] is passed",
    ]

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            self.build_param(name="target", type=str, default=None),
            self.build_param(name="recursive", type=bool, default=False)
        ]

    def __call__(self, tasks:dict, plugins:dict):
        for x in self._collect_locations():
            self._clean_single_loc(x)


    def _collect_locations(self) -> list[pl.Path]:
        cleanable = [doot.locs[x] for x in doot.locs
                     if doot.locs.metacheck(x, doot.locs.locmeta.cleanable)]
        return cleanable

    def _clean_single_loc(self, loc):
        if not loc.exists():
            pass
        self._print_text([f"- Cleaning: {loc}"])
        if loc.is_dir():
            shutil.rmtree(x)
        else:
            loc.unlink(missing_ok=True)
