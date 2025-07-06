#!/usr/bin/env python3
"""

"""
# ruff: noqa: F401
# Imports:
from __future__ import annotations

# ##-- 3rd party imports
from jgdv import Proto, Maybe

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
    from jgdv import VerStr
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable
    from jgdv.structs.chainguard import ChainGuard

##--|
from jgdv.cli._interface import CLIParamProvider_p
# isort: on
# ##-- end types

@runtime_checkable
class AcceptsSubcmds_p(Protocol):
    """ Protocol for marking cmds as able to allow subcmds in cli parsing """

    def _accept_subcmds(self) -> Literal[True]: ...

@runtime_checkable
class Command_p(CLIParamProvider_p, Protocol):
    """
    Holds command information and performs it
    """

    @property
    def name(self) -> str: ...
    @property
    def help(self) -> list[str]: ...
    @property
    def helpline(self) -> str: ...
    ##--|
    def __call__(self, idx:int, jobs:ChainGuard, plugins:ChainGuard):
        pass

    def shutdown(self, tasks:ChainGuard, plugins:ChainGuard, errored:Maybe[Exception]=None) -> None:
        """
          A Handler called on doot shutting down. only the triggered cmd's shutdown gets called
        """
        pass
