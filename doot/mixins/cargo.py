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

cargo_config    = tomler.load("Cargo.toml")
cargo_subconfig = tomler.load("./.cargo/config.toml")

package_name  : Final = cargo_config.package.name
build_path    : Final = cargo_subconfig.on_fail(str(doot.locs.build)).build.target_dir()
profiles      : Final = ["release", "dev"] + cargo_config.on_fail([]).profile()
binaries      : Final = [x.get('name') for x in  cargo_config.on_fail([], list).bin()]
lib_path      : Final = cargo_config.on_fail(None, None|str).lib.path()

class CargoMixin:

    def get_cargo_params(self):
        """
        Default param generator for cargo to get binaries and profiles
        """
        default_target = ""
        if bool(binaries):
            default_target = binaries[0]

        return [
            { "name": "profile", "type": str, "short": "p", "default": "dev", "choices": [(x,"") for x in profiles] },
            { "name": "target",  "type": str, "short": "t", "default": default_target, "choices": [(x, "") for x in binaries]},
        ]

    def cargo_do(self, action, *args, **kwargs):
        """
        builds a cargo action
        """
        return self.cmd(cargo, action, *args, *(val for x,y in kwargs.items() for val in (f"--{x}", y)))
