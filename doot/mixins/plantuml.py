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

plant_ext    = doot.config.on_fail("png", str).plantuml.ext()

class PlantUMLMixin:

    def plantuml_params(self):
        return [
            { "name" : "ext",    "type": str,   "short": "e", "default": plant_ext}
            ]

    def plantuml_img(self, dst, src, check=False) -> list:
        if check:
            return ["plantuml", "-checkonly", src]

        return [
            "plantuml", f"-t{self.args['ext']}",
            "-output", dst.resovle().parent
            "-filename", dst.stem,
            src
            ]
