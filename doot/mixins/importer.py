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

    def import_task(self, pathname:None|str):
        """
          given a path in the form `package.sub.sub:Class`, import the package, and return the named class.
        """
        if pathname is None:
            return None
        try:
            if pathname in ACTION_CTORS:
                return ACTION_CTORS[pathname].load()

            logging.info("Importing: %s", pathname)
            module_name, cls_name = pathname.split(IMPORT_SEP)
            module = importlib.import_module(module_name)
            return getattr(module, cls_name)
        except ImportError as err:
            raise doot.errors.DootTaskLoadError("Import Failed: %s : %s", pathname, err.msg, task=self.spec) from err
        except (AttributeError, KeyError) as err:
            raise doot.errors.DootTaskLoadError("Import Failed: Module has missing attribute/key: %s", pathname, task=self.spec) from err
        except ValueError as err:
            raise doot.errors.DootTaskLoadError("Import Failed: Can't split %s", pathname, task=self.spec) from err


    def import_callable(self, pathname:None|str) -> None|callable[Any]:
        """
          given a path in the form `package.sub.sub:function`, import the package, and return the named function.
        """
        if pathname is None:
            return None

        if pathname in ACTION_CTORS:
            return ACTION_CTORS[pathname].load()

        try:
            logging.info("Importing: %s", pathname)
            module_name, fun_name = pathname.split(IMPORT_SEP)
            module                = importlib.import_module(module_name)
            fun                   = getattr(module, fun_name)
            assert(callable(fun))
            return fun
        except ImportError as err:
            raise doot.errors.DootTaskLoadError("Import Failed: %s : %s", pathname, err.msg, task=self.spec) from err
        except (AttributeError, KeyError) as err:
            raise doot.errors.DootTaskLoadError("Import Failed: Module has missing attribute/key: %s", pathname, task=self.spec) from err
        except ValueError as err:
            raise doot.errors.DootTaskLoadError("Import Failed: Can't split %s", pathname, task=self.spec) from err

    def import_class(self, pathname:None|str, *, is_task_ctor=False) -> None|type[Any]:
        """
          given a path in the form `package.sub.sub:Class`, import the package, and return the named class.
        """
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
            raise doot.errors.DootInvalidConfig("Import Failed: %s : %s", pathname, err.msg) from err
        except (AttributeError, KeyError) as err:
            raise doot.errors.DootInvalidConfig("Import Failed: Module has missing attribute/key: %s", pathname) from err
        except ValueError as err:
            raise doot.errors.DootInvalidConfig("Import Failed: Can't split %s", pathname) from err
