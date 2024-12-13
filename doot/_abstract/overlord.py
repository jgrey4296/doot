"""

"""
from __future__ import annotations
import pathlib as pl
from abc import abstractmethod
from typing import NewType, Any

from jgdv import Maybe
from jgdv.structs.chainguard import ChainGuard
from doot._abstract.loader import Loaders_p


class Overlord_p:
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
