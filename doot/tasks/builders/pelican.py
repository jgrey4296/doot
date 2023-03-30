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

import sys
import datetime
import tomler

from doot import config
from doot.tasker import DootTasker

from pelican import Pelican
from pelican.settings import DEFAULT_CONFIG

class PelicanTasker(DootTasker):
    """
    A Generalized pelican task access point
    """

    def __init__(self, name="pelican::build", locs=None):
        super().__init__(name, locs)
        self.pelican_settings = {}
        self.pelican          = None
        locs.ensure("site", task=name)

    def setup_detail(self, task):
        task.update({
                "actions": [ self.load_pelican_settings]
        })
        return tas

    def load_pelican_settings(self):
        data = tomler.load(locs.pelican_settings)
        # TODO flatten properly
        self.pelican_settings.update(dict(data))
        self.pelican = Pelican(self.pelican_settings)

    def task_detail(self, task):
        task.update({
            "actions" : [ self.pelican_build ]
        })
        return task

    def clean(self, task):
        for x in self.locs.site_build.iterdir():
            if x.name[0] == ".":
                continue
            if x.is_dir():
                x.rmdir()
            else:
                x.rm()

    def pelican_build(self):
        self.pelican.run()
