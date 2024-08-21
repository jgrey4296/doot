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
import logging.handlers as l_handlers
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

env           : dict        = os.environ
IS_PRE_COMMIT : Final[bool] = "PRE_COMMIT" in env
Regexp        : TypeAlias   = str
MAX_FILES     : Final[int]  = 5
TARGETS       : Final[list[str]] = ["file", "stdout", "stderr", "rotate", "pass"]
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
        if bool(self.allowed):
            raise NotImplementedError("Logging Allows are not implemented yet")

    def __call__(self, record):
        if record.name in ["root", "__main__"]:
            return True
        if not (bool(self.allowed) or bool(self.rejections)):
            return True

        rejected = False
        rejected |= any(x in record.name for x in self.rejections)
        # rejected |= not self.name_re.match(record.name)
        return not rejected

class HandlerBuilder_m:
    """
    Loggerspec Mixin for building handlers
    """

    def _build_streamhandler(self) -> logmod.Handler:
        return logmod.StreamHandler(stdout)

    def _build_errorhandler(self) -> logmod.Handler:
        return logmod.StreamHandler(stderr)

    def _build_filehandler(self, path:pl.Path) -> logmod.Handler:
        return logmod.FileHandler(log_file_path, mode='w')

    def _build_rotatinghandler(self, path:pl.Path) -> logmod.Handler:
        handler = l_handlers.RotatingFileHandler(path, backupCount=MAX_FILES)
        handler.doRollover()
        return handler

    def _discriminate_handler(self, target:None|str|pl.Path) -> tuple[None|logmod.Handler, None|logmod.Formatter]:
        handler, formatter = None, None

        match target:
            case "pass" | None:
                return None, None
            case "file":
                log_file_path      = self.logfile()
                handler            = self._build_filehandler(log_file_path)
            case "rotate":
                log_file_path      = self.logfile()
                handler            = self._build_rotatinghandler(log_file_path)
            case "stdout":
                handler   = self._build_streamhandler()
            case "stderr":
                handler = self._build_errorhandler()
            case _:
                raise ValueError("Unknown logger spec target", target)

        match self.colour or IS_PRE_COMMIT:
            case _ if isinstance(handler, (logmod.FileHandler, l_handlers.RotatingFileHandler)):
                formatter = DootColourStripFormatter(fmt=self.format)
            case False:
                formatter = DootColourStripFormatter(fmt=self.format)
            case True:
                formatter = DootColourFormatter(fmt=self.format)

        assert(handler is not None)
        assert(formatter is not None)
        return handler, formatter

class LoggerSpec(BaseModel, HandlerBuilder_m, Buildable_p, metaclass=ProtocolModelMeta):
    """
      A Spec for toml defined logging control.
      Allows user to name a logger, set its level, format,
      filters, colour, and what verbosity it activates on,
      and what file it logs to.

      When 'apply' is called, it gets the logger,
      and sets any relevant settings on it.
    """

    name                       : str
    disabled                   : bool                        = False
    base                       : None|str                    = None
    level                      : str|int                     = logmod._nameToLevel.get("WARNING", 0)
    format                     : str                         = "{levelname:<8} : {message}"
    filter                     : list[str]                   = []
    allow                      : list[str]                   = []
    colour                     : bool|str                    = False
    verbosity                  : int                         = 1
    target                     : None|str|list[str|pl.Path]  = None # stdout | stderr | file
    filename_fmt               : None|str                    = "doot-%Y-%m-%d::%H:%M.log"
    propagate                  : None|bool                   = False
    clear_handlers             : bool                        = False
    nested                     : list[LoggerSpec]            = []

    RootName                   : ClassVar[str]               = "root"

    @staticmethod
    def build(data:list|dict, **kwargs) -> LoggerSpec:
        """
          Build a single spec, or multiple logger specs targeting the same logger
        """
        match data:
            case list():
                nested = []
                for x in data:
                    nested.append(LoggerSpec.build(x, **kwargs))
                return LoggerSpec(nested=nested, **kwargs)
            case TomlGuard():
                as_dict = data._table().copy()
                as_dict.update(kwargs)
                return LoggerSpec.model_validate(as_dict)
            case dict():
                as_dict = data.copy()
                as_dict.update(kwargs)
                return LoggerSpec.model_validate(as_dict)

    @field_validator("level")
    def _validate_level(cls, val):
        return logmod._nameToLevel.get(val, 0)

    @field_validator("format")
    def _validate_format(cls, val):
        return val

    @field_validator("target")
    def _validate_target(cls, val):
        match val:
            case [*xs] if all(x in TARGETS for x in xs):
                return val
            case str() if val in TARGETS:
                return val
            case pl.Path():
                return val
            case None:
                return "stdout"
            case _:
                raise ValueError("Unknown target value for LoggerSpec", val)

    @ftz.cached_property
    def fullname(self) -> str:
        if self.base is None:
            return self.name
        return "{}.{}".format(self.base, self.name)

    def apply(self, *, onto:None|logmod.Logger=None):
        """ Apply this spec (and nested specs) to the relevant logger """
        handler_pairs : list[tuple[logmod.Handler, logmod.Formatter]] = []
        logger                                                        = self.get()
        logger.propagate                                              = self.propagate
        logger.setLevel(logmod._nameToLevel.get("NOTSET", 0))
        if self.disabled:
            logger.disabled = True
            return logger

        match self.target:
            case _ if bool(self.nested):
                for subspec in self.nested:
                    subspec.apply()
                return logger
            case None | []:
                handler_pairs.append(self._discriminate_handler(None))
            case [*xs]:
                handler_pairs += [self._discriminate_handler(x) for x in xs]
            case str() | pl.Path():
                handler_pairs.append(self._discriminate_handler(self.target))
            case _:
                raise ValueError("Unknown target value for LoggerSpec", self.target)

        log_filter       = None
        if bool(self.allow) or bool(self.filter):
            log_filter = _AnyFilter(allow=self.allow, reject=self.filter)

        for pair in handler_pairs:
            match pair:
                case None, _:
                    pass
                case hand, None:
                    hand.setLevel(self.level)
                    if log_filter is not None:
                        hand.addFilter(log_filter)
                    logger.addHandler(hand)
                case hand, fmt:
                    hand.setLevel(self.level)
                    hand.setFormatter(fmt)
                    if log_filter is not None:
                        hand.addFilter(log_filter)
                    logger.addHandler(hand)
                case _:
                    pass
        else:
            if not bool(logger.handlers):
                logger.setLevel(self.level)
                logger.propagate = True
            return logger

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
