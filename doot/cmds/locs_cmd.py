#!/usr/bin/env python3
"""
A Doot Command to report on defined locations
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

printer = logmod.getLogger("doot._printer")

from collections import defaultdict
from tomlguard import TomlGuard
import doot
import doot.errors
from doot.cmds.base_cmd import BaseCommand
from doot.structs import ParamSpec


INDENT : Final[str] = " "*8

@doot.check_protocol
class LocsCmd(BaseCommand):
    _name      = "locs"
    _help      = ["A simple command to list all config defined locations."]

    @property
    def param_specs(self) -> list[ParamSpec]:
        return super().param_specs + [
            self.build_param(name="all",                                          default=True,                   desc="List all loaded tasks, by group"),
            self.build_param(name="by-source",                                    default=False,                  desc="List all loaded tasks, by source file",  prefix="--"),
            self.build_param(name="pattern",                  type=str,           default="", positional=True,    desc="List tasks with a basic string pattern in the name"),
            ]

    def __call__(self, tasks:TomlGuard, plugins:TomlGuard):
        """List task generators"""
        logging.debug("Starting to List Locations")

        if not bool(doot.locs):
            printer.info("No Locations Defined")
            return

        self._print_all()

    def _print_matches(self, plugins):
        raise NotImplementedError()

    def _print_by_source(self, plugins):
        raise NotImplementedError()

    def _print_all(self):
        printer.info("Defined Locations:", extra={"colour":"cyan"})
        max_key = len(max(doot.locs, key=len))
        fmt_str = f"{INDENT}%-{max_key}s :: %-25s"
        locs = defaultdict(list)

        for name in doot.locs:
            printer.info(fmt_str, name, doot.locs[f"{{{name}}}"])

        printer.info("")
