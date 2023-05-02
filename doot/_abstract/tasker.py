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

class DootTasker_i:
    """
    builds task descriptions
    """

    def __init__(self, base:str|list, locs:DootLocData=None, output=None, subgroups=None):
        assert(base is not None)
        assert(locs is not None or locs is False), locs

        # Wrap in a lambda because MethodType does not behave as we need it to
        match base:
            case str():
                self.basename         = base
                self.subgroups        = subgroups or []
            case [x, *xs]:
                self.basename = x
                self.subgroups = xs + (subgroups or [])
            case _:
                raise TypeError("Bad base name provided to task: %s", base)

        self.locs             = locs
        self.args             = {}
        self._setup_name      = None
        self.has_active_setup = False
        self.output           = output

    @property
    def setup_name(self):
        pass

    @property
    def fullname(self):
        pass

    @property
    def doc(self):
        pass

    def set_params(self) -> list:
        return []

    def default_task(self) -> dict:
        return dict()

    def default_meta(self) -> dict:
        meta = dict()
        return meta

    def is_current(self, task:DootTask):
        return False

    def clean(self, task:DootTask):
        return

    def setup_detail(self, task:dict) -> None|dict:
        return task

    def task_detail(self, task:dict) -> dict:
        return task

    def log(self, msg, level=logmod.DEBUG, prefix=None):
        pass

    def build(self, **kwargs) -> GeneratorType:
        pass
