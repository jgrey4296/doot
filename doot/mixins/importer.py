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

import importlib
import doot.errors
from doot.constants import IMPORT_SEP
from doot._abstract.loader import PluginLoader_p

ACTION_CTORS = {}

if PluginLoader_p.loaded:
    ACTION_CTORS = {x.name : x for x in PluginLoader_p.loaded.action}

class ImporterMixin:

    def import_ctor(self, pathname:None|str):
        raise NotImplementedError("TODO")

    def import_function(self, pathname:None|str):
        raise NotImplementedError("TODO")

    def import_class(self, pathname:None|str, *, is_task_ctor=False):
        if pathname is None:
            return None
        try:
            if not is_task_ctor and pathname in ACTION_CTORS:
                return ACTION_CTORS[pathname].load()

            logging.info("Importing: %s", pathname)
            module_name, cls_name = pathname.split(IMPORT_SEP)
            module = importlib.import_module(module_name)
            return getattr(module, cls_name)
        except ImportError as err:
            breakpoint()
            pass
            raise doot.errors.DootTaskLoadError("Import Failed: %s", pathname, task=self.spec) from err
        except (AttributeError, KeyError) as err:
            raise doot.errors.DootTaskLoadError("Import Failed: Module has missing attritbue/key: %s", pathname, task=self.spec) from err
        except ValueError as err:
            raise doot.errors.DootTaskLoadError("Import Failed: Can't split %s", pathname, task=self.spec) from err
