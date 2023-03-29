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

from pelican import main as pelican_main
from pelican.server import ComplexHTTPRequestHandler, RootedHTTPServer
from pelican.settings import DEFAULT_CONFIG, get_settings_from_file


class PelicanTasker(DootTasker):
    """
    A Generalized pelican task access point
    """

    def __init__(self, name="pelican::build", locs=None):
        super().__init__(name, locs)

    def setup_detail(self, task):
        task.update({

        })
        return tas

    def load_pelican_settings(self):
        SETTINGS_FILE_BASE = 'pelicanconf.py'
        SETTINGS = {}
        SETTINGS.update(DEFAULT_CONFIG)
        LOCAL_SETTINGS = get_settings_from_file(SETTINGS_FILE_BASE)
        SETTINGS.update(LOCAL_SETTINGS)

        self.pelican_CONFIG = {
            'settings_base': SETTINGS_FILE_BASE,
            'settings_publish': 'publishconf.py',
            # Output path. Can be absolute or relative to tasks.py. Default: 'output'
            'deploy_path': SETTINGS['OUTPUT_PATH'],
            # Github Pages configuration
            'github_pages_branch': 'main',
            'commit_message': "'Publish site on {}'".format(datetime.date.today().isoformat()),
            # Host and port for `serve`
            'host': 'localhost',
            'port': 8000,
            }

    def task_detail(self, task):
        task.update({

        })
        return task

    def clean(self, task):
        pass

    def pelican_build(self):
        pass
