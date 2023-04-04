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

from pelican import Pelican, listen
from pelican.settings import DEFAULT_CONFIG, configure_settings

class PelicanTasker(DootTasker):
    """
    A Generalized pelican task access point
    """

    def __init__(self, name="pelican::build", locs=None):
        super().__init__(name, locs)
        self.pelican_settings = DEFAULT_CONFIG.copy()
        self.pelican          = None
        locs.ensure("site", "pelican_settings", task=name)

    def set_params(self):
        return [
            { "name": "build", "short": "b", "type": str, "default" : "dev"},
        ]

    def setup_detail(self, task):
        task.update({
                "actions": [ self.load_pelican_settings]
        })
        return task

    def load_pelican_settings(self):
        # Walk data, if key matches key in settings, copy it over
        data     = tomler.load(self.locs.pelican_settings)
        queue    = [([k], v) for k,v in dict(data).items()]
        while bool(queue):
            match queue.pop(0):
                case ["build", "config", k], v if k != self.args['build']:
                    pass
                case [k], v if k in self.pelican_settings:
                    self.pelican_settings[k] = v
                case [*ks, k], v if k in self.pelican_settings:
                    self.pelican_settings[k] = v
                case ks, dict() as v:
                    queue += [(ks + [k], v) for k,v in v.items()]
                case ks, list() as v:
                    queue += [(ks + ["__"], v2) for v2 in v]

        self.pelican_settings = configure_settings(self.pelican_settings)
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


class PelicanServer(PelicanTasker):

    def __init__(self, name="pelican::serve", locs=None):
        super().__init__(name, locs)

    def task_detail(self, task):
        task.update({
            "actions" : [ self.pelican_serve]
        })
        return task

    def pelican_serve(self):
        listen(self.pelican_settings.get('BIND'),
               self.pelican_settings.get('PORT'),
               self.pelican_settings.get("OUTPUT_PATH"))
