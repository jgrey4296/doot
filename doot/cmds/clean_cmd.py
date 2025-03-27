#!/usr/bin/env python3
"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import functools as ftz
import itertools as itz
import logging as logmod
import re
import shutil
import time
import types
from collections import defaultdict
# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Proto

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot._abstract import Command_p
from doot.cmds.core.cmd import BaseCommand

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    import pathlib as pl
##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

clean_locs = doot.config.on_fail([], list).settings.commands.clean.locs()

@Proto(Command_p)
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
        return [
            *super().param_specs,
            self.build_param(name="target", type=str, default=None),
            self.build_param(name="recursive", type=bool, default=False),
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
            shutil.rmtree(loc)
        else:
            loc.unlink(missing_ok=True)
