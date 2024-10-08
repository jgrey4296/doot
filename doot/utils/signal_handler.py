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
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

import os
import signal
import doot

##-- logging
logging    = logmod.getLogger(__name__)
printer    = doot.subprinter()
setup_l    = doot.subprinter("setup")
shutdown_l = doot.subprinter("shutdown")
##-- end logging

env : dict = os.environ

class SignalHandler:
    """ Install a breakpoint to run on (by default) SIGINT """

    def __init__(self):
        self._disabled = "PRE_COMMIT" in env

    @staticmethod
    def handle(signum, frame):
        breakpoint()
        pass

    @staticmethod
    def install(sig=signal.SIGINT):
        setup_l.debug("Installing Task Loop handler for: %s", signal.strsignal(sig))
        # Install handler for Interrupt signal
        signal.signal(sig, SignalHandler.handle)

    @staticmethod
    def uninstall(sig=signal.SIGINT):
        shutdown_l.debug("Uninstalling Task Loop handler for: %s", signal.strsignal(sig))
        signal.signal(sig, signal.SIG_DFL)

    def __enter__(self):
        if not self._disabled:
            SignalHandler.install()
        return

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if not self._disabled:
            SignalHandler.uninstall()
        # return False to reraise errors
        return
