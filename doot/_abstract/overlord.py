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
##-- end type checking

@runtime_checkable
class Overlord_p(Protocol):
    """
    Main entrypoint for doot
    """

    @staticmethod
    def print_version() -> str:
        raise NotImplementedError()

    @abstractmethod
    def __init__(self, *, loaders:Maybe[dict[str, Loaders_p]]=None,
                 configs:tuple[pl.Path|str]=('doot.toml', 'pyproject.toml'),
                 extra_config:Maybe[dict[str,Any]|ChainGuard]=None,
                 args:Maybe[list[str]]=None):
        raise NotImplementedError()

    def __call__(self, cmd:Maybe[str]=None) -> int:
        """entry point for all commands

        :param all_args: list of string arguments from command line

        return codes:
          0: tasks executed successfully
          1: one or more tasks failed
          2: error while executing a task
          3: error before task execution starts,
             in this case the Reporter is not used.
             So be aware if you expect a different formatting (like JSON)
             from the Reporter.
        """
        raise NotImplementedError()

    def shutdown(self) -> None:
        raise NotImplementedError()
