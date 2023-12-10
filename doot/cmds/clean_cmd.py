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
printer = logmod.getLogger("doot._printer")

import doot
import shutil
from doot._abstract import Command_i
from collections import defaultdict

clean_locs = doot.config.on_fail([], list).commands.clean.locs()


class CleanCmd(Command_i):
    """
      Runs either a general clean command, or a specific task clean command

    """
    _name      = "clean"
    _help      = [
        "Called with a -t[arget]={task}, will delete locations listed in that task's toml spec'd `clean_targets`",
        "Without a target, will delete locations listed in doot.toml's: `commands.clean.locs`",
        "Directories will *not* be deleted unless -r[ecursive] is passed",
        ]

    @property
    def param_specs(self) -> list:
        return super().param_specs + [
            self.make_param(name="target", type=str, default=None),
            self.make_param(name="recursive", type=bool, default=False)
            ]

    def __call__(self, tasks:dict, plugins:dict):
        clean_target = doot.args.on_fail(None).cmd.args.target()
        if clean_target is None:
            printer.info("- No Clean Target Specified.")
            existing_clean_targets = list(filter(lambda x: x.exists(), [doot.locs[x] for x in clean_locs]))
            self._gen_clean(existing_clean_targets)
        elif clean_target in tasks:
            self._task_clean(tasks[clean_target])
        elif clean_target not in tasks:
            printer.error("Specified Target not found in task list: %s", clean_target)

    def _task_clean(self, task):
        printer.info("Cleaning Task: %s", task.name)
        task_clean_locs = task.extra.on_fail([], list).clean_locs()
        existing_clean_targets = list(filter(lambda x: x.exists(), [doot.locs[x] for x in task_clean_locs]))
        self._gen_clean(existing_clean_targets)


    def _gen_clean(self, existing_clean_targets):
        if not bool(existing_clean_targets):
            printer.info("- No Viable Clean Locations.")
            return

        printer.info("- Clean will *delete* the following locations:")
        printer.info("")
        for loc in existing_clean_targets:
            printer.info("-- %s", str(loc))

        printer.info("")
        match input(":-- WARNING: Do you want to clean? Yes/_: "):
            case "Yes":
                for loc in existing_clean_targets:
                    match input(f"--- Delete {loc} ? Y/_: "):
                        case "Y" if loc.is_dir() and doot.args.cmd.args.recursive:
                            printer.info("---- Deleting Recursively")
                            shutil.rmtree(loc)
                        case "Y" if loc.is_dir():
                            printer.info("---- Deleting Non-Recursively")
                            try:
                                loc.rmdir()
                            except OSError:
                                printer.info("---- Location is not empty, to delete recursively, pass -r to clean")
                        case "Y" if loc.is_file():
                            printer.info("---- Deleting")
                            loc.unlink()
                        case _:
                            printer.info("---- Skipping")

            case _:
                printer.info("Not cleaning.")
