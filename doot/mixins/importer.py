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
from doot.constants import IMPORT_SEP
from doot._abstract.loader import PluginLoader_p
import doot.errors

if PluginLoader_p.loaded:
    ACTION_CTORS = {x.name : x.load() for x in PluginLoader_p.loaded.action}
else:
    ACTION_CTORS = {}

class ImporterMixin:

    def import_class(self, pathname:str):
        try:
            if pathname in ACTION_CTORS:
                return ACTION_CTORS[pathname]

            logging.info("Importing: %s", pathname)
            module_name, cls_name = pathname.split(IMPORT_SEP)
            module = importlib.import_module(module_name)
            return getattr(module, cls_name)
        except ImportError as err:
            raise doot.errors.DootTaskLoadError("Import Failed: %s", module_name, task=self.spec) from err
        except (AttributeError, KeyError) as err:
            raise doot.errors.DootTaskLoadError("Import Failed: Module %s has no: %s", module_name, cls_name, task=self.spec) from err
        except ValueError as err:
            raise doot.errors.DootTaskLoadError("Import Failed: Can't split %s", pathname, task=self.spec) from err
