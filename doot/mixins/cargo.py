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

import tomler
import shutil
import doot

cargo  = shutil.which("cargo")
rustup = shutil.which("rustup")

cargo_config    = Tomler.load("Cargo.toml")
cargo_subconfig = Tomler.load("./.cargo/config.toml")

package_name  : Final = cargo_config.package.name
build_path    : Final = cargo_subconfig.on_fail(str(doot.locs.build)).build.target_dir()
profiles      : Final = ["release", "debug", "dev"] + cargo_config.on_fail([]).profile()
binaries      : Final = [x.get('name') for x in  cargo_config.on_fail([], list).bin()]
lib_path      : Final = cargo_config.on_fail(None, None|str).lib.path()

class CargoMixin:

    def get_cargo_params(self):
        """

        Default param generator for cargo to get binaries and profiles
        """
        return [
            { "name": "profile", "type": str, "short": "p", "default": "debug", "choices": [(x,"") for x in profiles] },
            { "name": "target",  "type": str, "short": "t", "default": binaries[0], "choices": [(x, "") for x in binaries]},
        ]

    def _cargo_action(self, *args) -> CmdAction:
        return self.cmd(cargo, *args)

    def cargo_do(self, action, *args, **kwargs):
        return self._cargo_action(action, *args, *(val for x,y in kwargs.items() for val in (f"--{x}", y)))
