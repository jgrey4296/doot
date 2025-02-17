"""

"""
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import inspect
import itertools as itz
import logging as logmod
import pathlib as pl
import sys
import textwrap
from abc import abstractmethod
from collections import defaultdict, deque
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Maybe, VerStr
from jgdv.structs.chainguard import ChainGuard

# ##-- end 3rd party imports

# ##-- 1st party imports
from doot._abstract.protocols import CLIParamProvider_p

# ##-- end 1st party imports

##-- end imports

class Command_i(CLIParamProvider_p):
    """
    Holds command information and performs it
    """

    _name : Maybe[str]       = None # if not specified uses the class name
    _help : Maybe[list[str]] = None

    _version : VerStr = "0.1"

    @property
    @abstractmethod
    def name(self):
        """get command name as used from command line"""
        pass

    @property
    @abstractmethod
    def help(self) -> list[str]:
        pass

    @property
    @abstractmethod
    def helpline(self) -> str:
        """ get just the first line of the help text """
        pass

    @abstractmethod
    def __call__(self, jobs:ChainGuard, plugins:ChainGuard):
        pass

    def shutdown(self, tasks, plugins, errored=None):
        """
          A Handler called on doot shutting down. only the triggered cmd's shutdown gets called
        """
        pass
