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

class FilerMixin:

    def rmglob(self, root:pl.Path, *args):
        for x in args:
            for y in root.glob(x):
                y.unlink()

    def rmfiles(self, *args):
        for x in args:
            x.unlink(missing_ok=True)

    def rmdirs(self, *locs:pl.Path):
        logging.debug("Removing Directories: %s", locs)
        for target in locs:
            if not target.exists():
                logging.warning("Non-existent rmdir: %s", target)
                continue
            shutil.rmtree(target)

    def mkdirs(self, *locs:pl.Path):
        for target in locs:
            if not target.exists():
                logging.debug("Making Directory: %s", target)
                target.mkdir(parents=True, exist_ok=True)

    def write_to(self, fpath, key:str|list[str], task, sep=None):
        if sep is None:
            sep = "\n--------------------\n"
        match key:
            case str():
                value = task.values[key]
            case [*strs]:
                value = sep.join([task.values[x] for x in key])

        fpath.write_text(value)

    def append_to(self, fpath, key:str|list[str], task, sep=None):
        if sep is None:
            sep = "\n--------------------\n"

        match key:
            case str():
                value = task.values[key]
            case [*strs]:
                value = sep.join([task.values[x] for x in key])

        with open(fpath, 'a') as f:
            f.write(value)

    def move_to(self, fpath:pl.Path, *args, fn=None):
        """
        Move *args to fpath, with fn as the naming strategy
        only overwrite if is_backup is true
        if fpath is a file, only one arg is allowed
        """
        # Set the naming strategy:
        assert(fpath.parent.exists())
        overwrite = True
        match fn:
            case types.FunctionType() | types.MethodType() | types.LambdaType():
                pass
            case "overwrite":
                fn = lambda d, x: d / x.name
            case "backup":
                fn = lambda d, x: d / f"{x.parent.name}_{x.name}_backup"
            case "file":
                assert(not fpath.is_dir())
                fn = lambda d, x: d
            case _ if len(args) == 1:
                fn        = lambda d, x: d
            case _:
                assert(fpath.exists() and fpath.is_dir())
                overwrite = False
                fn        = lambda d, x: d / x.name

        # Then do the move
        for x in args:
            target_path = fn(fpath, x)
            if not overwrite and target_path.exists():
                 logging.warning("Not Moving: %s -> %s", x, target_path)
                 continue
            logging.debug("Renaming: %s -> %s", x, target_path)
            x.rename(target_path)

    def copy_to(self, fpath ,*args, fn=None):
        assert(fpath.parent.exists())
        overwrite = True
        match fn:
            case types.FunctionType() | types.MethodType() | types.LambdaType():
                pass
            case "overwrite":
                fn = lambda d, x: d / x.name
            case "backup":
                fn = lambda d, x: d / f"{x.parent.name}_{x.name}_backup"
            case "file":
                assert(not fpath.is_dir())
                fn = lambda d, x: d
            case _:
                overwrite = False
                fn = lambda d, x: d / x.name

        for x in args:
            target_name = fn(fpath, x)
            if not overwrite and target_name.exists():
                logging.warning("File Exists already: %s -> %s", x, target_name)
                continue
            match x.is_file():
                case True:
                    shutil.copy(x, target_name)
                case False:
                    shutil.copytree(x, target_name, dirs_exist_ok=True)
