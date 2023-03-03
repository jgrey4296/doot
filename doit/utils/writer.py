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

class Writer:
    """Write to N streams.

    This is used on python-actions to allow the stream to be output to terminal
    and captured at the same time.
    """
    def __init__(self, *writers):
        """@param writers - file stream like objects"""
        self.writers = []
        self.orig_stream = None  # The original stream terminal/file
        for writer in writers:
            self.add_writer(writer)

    def add_writer(self, stream, *, is_original=False):
        """adds a stream to the list of writers
        @param is: (bool) if specified overwrites real isatty from stream
        """
        self.writers.append(stream)
        if is_original:
            self.orig_stream = stream

    def write(self, text):
        """write 'text' to all streams"""
        for stream in self.writers:
            stream.write(text)

    def flush(self):
        """flush all streams"""
        for stream in self.writers:
            stream.flush()

    def isatty(self):
        if self.orig_stream:
            return self.orig_stream.isatty()
        return False

    def fileno(self):
        if self.orig_stream:
            return self.orig_stream.fileno()
        raise io.UnsupportedOperation()
