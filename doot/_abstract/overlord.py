"""

"""
from __future__ import annotations
from abc import abstractmethod
from typing import NewType, Any, Protocol, runtime_checkable

##-- type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from doot._abstract import Loaders_p
    from jgdv import Maybe
    from jgdv.structs.chainguard import ChainGuard
    import pathlib as pl
    type Logger = logmod.Logger
##-- end type checking

@runtime_checkable
class Overlord_p(Protocol):
    """
    protocol for the doot accesspoint,
    used for setting up and using Doot programmatically
    """

    def setup(self, *, targets:Maybe[list[pl.Path]|False]=None, prefix:Maybe[str]) -> None:
        pass

    def subprinter(self, name:Maybe[str]=None, *, prefix=None) -> Logger:
        pass

@runtime_checkable
class Main_p(Protocol):
    """
    protocol for doot as a main program
    """

    def __init__(self, *, args:Maybe[list]=None) -> None:
        pass

    def main(self) -> None:
        pass

    def run_cmd(self, cmd:Maybe[str]=None) -> int:
        pass

    def shutdown(self) -> None:
        raise NotImplementedError()
