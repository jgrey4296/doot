#!/usr/bin/env python3
"""

"""
# ruff: noqa: F401
# Imports:
from __future__ import annotations

# ##-- 3rd party imports
from jgdv import Proto, Maybe, VerStr

# ##-- end 3rd party imports

# ##-- 1st party imports

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
from abc import abstractmethod
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from jgdv.structs.chainguard import ChainGuard

##--|
from doot._abstract.protocols import CLIParamProvider_p
# isort: on
# ##-- end types

class Command_d:
    _name    : Maybe[str]           = None
    _help    : Maybe[Iterable[str]] = None

    _version : VerStr               = "0.1"

class Command_p(CLIParamProvider_p, Protocol):
    """
    Holds command information and performs it
    """

    @property
    @abstractmethod
    def name(self) -> str:
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

    def shutdown(self, tasks, plugins, errored=None) -> None:
        """
          A Handler called on doot shutting down. only the triggered cmd's shutdown gets called
        """
        pass
