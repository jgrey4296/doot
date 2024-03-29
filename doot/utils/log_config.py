#!/usr/bin/env python3
"""

"""

##-- builtin imports
from __future__ import annotations

# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1

##-- end builtin imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

import os
from sys import stdout, stderr
import doot
import doot.constants
from doot.utils.log_colour import DootColourFormatter, DootColourStripFormatter

env : dict = os.environ

class _DootAnyFilter:
    """

    """

    def __init__(self, names=None, reject=None):
        self.names      = names or []
        self.rejections = reject or []
        self.name_re    = re.compile("^({})".format("|".join(self.names)))

    def __call__(self, record):
        return (record.name not in self.rejections) and (record.name == "root"
                                                         or not bool(self.names)
                                                    or self.name_re.match(record.name))

class DootLogConfig:
    """ Utility class to setup [stdout, stderr, file] logging. """

    def __init__(self):
        # Root Logger for everything
        self.root    = logmod.root
        # EXCEPT this, which replaces 'print(x)'
        self.printer               = logmod.getLogger(doot.constants.PRINTER_NAME)

        self.file_handler          = logmod.FileHandler(pl.Path() / "log.doot", mode='w')
        self.stream_handler        = logmod.StreamHandler(stdout)
        self.print_stream_handler  = logmod.StreamHandler(stdout)

        self._setup()

    def _setup(self):
        """ a basic, config-less setup """
        self.root.setLevel(logmod.NOTSET)
        self.file_handler.setFormatter(DootColourStripFormatter(fmt="{levelname} : INIT : {message}"))

        self.stream_handler.setLevel(logmod.WARNING)
        self.stream_handler.setFormatter(logmod.Formatter("{levelname}  : INIT : {message}", style="{"))

        self.root.addHandler(self.file_handler)
        self.root.addHandler(self.stream_handler)

        self.printer.propagate = False
        self.print_stream_handler.setFormatter(logmod.Formatter("{message}", style="{"))
        self.printer.setLevel(logmod.NOTSET)
        self.printer.addHandler(self.print_stream_handler)
        self.printer.addHandler(self.file_handler)

    def setup(self):
        """ a setup that uses config values """
        assert(doot.config is not None)
        self._setup_file_logging()
        self._setup_stream_logging()
        self._setup_print_logging()

    def _setup_file_logging(self):
        file_log_level    = doot.config.on_fail("DEBUG", str|int).logging.file.level(wrapper=lambda x: logmod._nameToLevel.get(x, 0))
        file_log_format   = doot.config.on_fail("{levelname} : {pathname} : {lineno} : {funcName} : {message}", str).logging.file.format()
        file_filter_names = doot.config.on_fail([], list).logging.file.allow()

        self.file_handler.setLevel(file_log_level)
        self.file_handler.setFormatter(DootColourStripFormatter(fmt=file_log_format))
        if bool(file_filter_names):
            self.file_handler.addFilter(_DootAnyFilter(file_filter_names))

    def _setup_stream_logging(self):
        stream_log_level    = doot.config.on_fail("WARNING", str|int).logging.stream.level(wrapper=lambda x: logmod._nameToLevel.get(x, 0))
        stream_log_format   = doot.config.on_fail("{levelname} : {pathname} : {lineno} : {funcName} : {message}", str).logging.stream.format()
        stream_filter_names = doot.config.on_fail([], list).logging.stream.allow()

        self.stream_handler.setLevel(stream_log_level)
        use_colour = doot.config.on_fail(False, bool).logging.stream.colour()
        use_colour &= "PRE_COMMIT" not in env
        if use_colour:
            self.stream_handler.setFormatter(DootColourFormatter(fmt=stream_log_format))
        else:
            self.stream_handler.setFormatter(DootColourStripFormatter(fmt=stream_log_format))

        if bool(stream_filter_names):
            self.stream_handler.addFilter(_DootAnyFilter(stream_filter_names))

    def _setup_print_logging(self):
        printer_log_level    = doot.config.on_fail("NOTSET", str|int).logging.printer.level(wrapper=lambda x: logmod._nameToLevel.get(x, 0))
        printer_log_format   = doot.config.on_fail("{message}", str).logging.printer.format()

        self.print_stream_handler.setLevel(printer_log_level)

        use_colour = doot.config.on_fail(False, bool).logging.printer.colour()
        use_colour &= "PRE_COMMIT" not in env
        if use_colour:
            self.print_stream_handler.setFormatter(DootColourFormatter(fmt=printer_log_format))
        else:
            self.print_stream_handler.setFormatter(DootColourStripFormatter(fmt=printer_log_format))

    def set_level(self, level):
        self.stream_handler.setLevel(level)
