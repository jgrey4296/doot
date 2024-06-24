#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import os
import pathlib as pl
import re
import time
import types
import weakref
from sys import stderr, stdout
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from pydantic import (BaseModel, Field, ValidationError, field_validator,
                      model_validator)
from tomlguard import TomlGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot.utils.log_colour import DootColourFormatter, DootColourStripFormatter
from doot._abstract.protocols import Buildable_p, ProtocolModelMeta

# ##-- end 1st party imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

env : dict = os.environ
Regexp : TypeAlias = str

class _AnyFilter:
    """
      A Simple filter to reject based on:
      1) a whitelist of regexs,
      2) a simple list of rejection names

    """

    def __init__(self, allow:None|list[Regexp]=None, reject:None|list[str]=None):
        self.allowed    = allow or []
        self.rejections = reject or []
        self.allowed_re    = re.compile("^({})".format("|".join(self.allowed)))

    def __call__(self, record):
        if record.name in ["root", "__main__"]:
            return True
        if not bool(self.allowed):
            return True
        if not bool(self.rejections):
            return True

        rejected = False
        rejected |= record.name in self.rejections
        rejected |= not self.name_re.match(record.name)
        return not rejected


class LoggerSpec(BaseModel, Buildable_p, metaclass=ProtocolModelMeta):
    """
      A Spec for toml defined logging control.
      Allows user to name a logger, set its level, format,
      filters, colour, and what verbosity it activates on,
      and what file it logs to.

      When 'apply' is called, it gets the logger,
      and sets any relevant settings on it.
    """

    name                       : str
    base                       : None|str              = None
    level                      : str|int               = logmod._nameToLevel.get("NOTSET", 0)
    format                     : str                   = "{levelname:<8} : {message}"
    filter                     : list[str]             = []
    allow                      : list[str]             = []
    colour                     : bool|str              = False
    verbosity                  : int                   = 1
    target                     : None|str|pl.Path      = None # stdout | stderr | file
    filename_fmt               : None|str              = "doot-%Y-%m-%d::%H:%M.log"
    propagate                  : None|bool             = False
    clear_handlers             : bool                  = False
    nested                     : list[LoggerSpec]      = []

    RootName                   : ClassVar[str]         = "root"

    @staticmethod
    def build(data:list|dict, *, name:None|str=None) -> LoggerSpec:
        """
          Build a single spec, or multiple logger specs targeting the same logger
        """
        match data:
            case list():
                nested = []
                for x in data:
                    nested.append(LoggerSpec.build(x, name=name))
                return LoggerSpec(name=name, nested=nested)
            case TomlGuard():
                as_dict = data._table().copy()
                if name:
                    as_dict['name'] = name
                return LoggerSpec.model_validate(as_dict)
            case dict():
                if name:
                    data['name'] = name
                return LoggerSpec.model_validate(data)

    @field_validator("level")
    def _validate_level(cls, val):
        return logmod._nameToLevel.get(val, 0)

    @field_validator("format")
    def _validate_format(cls, val):
        return val

    @field_validator("target")
    def _validate_target(cls, val):
        match val:
            case str() if val in ["file", "stdout", "stderr"]:
                return val
            case pl.Path():
                return val
            case None:
                return "stdout"
            case _:
                raise ValueError("Unknown target value for LoggerSpec", self.target)

    @ftz.cached_property
    def fullname(self) -> str:
        if self.base is None:
            return self.name
        return "{}.{}".format(self.base, self.name)

    def _build_streamhandler(self) -> logmod.Handler:
        return logmod.StreamHandler(stdout)

    def _build_errorhandler(self) -> logmod.Handler:
        return logmod.StreamHandler(stderr)

    def _build_filehandler(self) -> logmod.Handler:
        log_file_path      = self.logfile()
        return logmod.FileHandler(log_file_path, mode='w')

    def apply(self, *, onto:None|logmod.Logger=None):
        logger = self.get()
        logger.setLevel("NOTSET")
        filter = None
        if bool(self.allow) or bool(self.filter):
            filter = _AnyFilter(allow=self.allow, reject=self.filter)

        match self.target:
            case _ if bool(self.nested):
                for subspec in self.nested:
                    subspec.apply()
                return
            case "file":
                handler   = self._build_filehandler()
                formatter = DootColourStripFormatter(fmt=self.format)
            case "stdout" if not self.colour or "PRE_COMMIT" in env:
                handler   = self._build_streamhandler()
                formatter = DootColourStripFormatter(fmt=self.format)
            case "stdout":
                assert(self.colour)
                handler = self._build_streamhandler()
                formatter = DootColourFormatter(fmt=self.format)
            case "stderr" if not self.colour:
                handler = self._build_errorhandler()
                formatter = DootColourStripFormatter(fmt=self.format)
            case "stderr":
                assert(self.colour)
                handler = self._build_errorhandler()
                formatter = DootColourStripFormatter(fmt=self.format)
            case None:
                handler   = self._build_streamhandler()
                formatter = DootColourStripFormatter(fmt=self.format)
            case _:
                raise ValueError("Unknown target value for LoggerSpec", self.target)


        handler.setLevel(self.level)
        handler.setFormatter(formatter)
        if filter is not None:
            handler.addFilter(filter)

        logger.addHandler(handler)
        if self.propagate is not None:
            logger.propagate = self.propagate

    def get(self) -> logmod.Logger:
        return logmod.getLogger(self.fullname)

    def clear(self):
        """ Clear the handlers for the logger referenced """
        logger = self.get()
        handlers = logger.handlers[:]
        for h in handlers:
            logger.removeHandler(h)

    def logfile(self) -> pl.Path:
        log_dir  = doot.locs["{logs}"]
        if not log_dir.exists():
            log_dir = pl.Path()

        filename = datetime.datetime.now().strftime(self.filename_fmt)
        return log_dir / filename

    def set_level(self, level:int|str):
        match level:
            case str():
                level = logmod._nameToLevel.get(level, 0)
            case int():
                pass
        logger = self.get()
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)
