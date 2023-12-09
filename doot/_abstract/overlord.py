"""

"""
from __future__ import annotations
import pathlib as pl
from abc import abstractmethod
from typing import NewType, Any

from tomlguard import TomlGuard
from doot._abstract.parser import ParamSpecMaker_m
from doot._abstract.loader import Loaders_p


class Overlord_p(ParamSpecMaker_m):
    """
    Main entrypoint for doot
    """

    @staticmethod
    def print_version() -> str:
        raise NotImplementedError()

    @abstractmethod
    def __init__(self, *, loaders:dict[str, Loaders_p]|None=None,
               configs:tuple[pl.Path|str]=('doot.toml', 'pyproject.toml'),
               extra_config:dict[str,Any]|TomlGuard|None=None,
               args:list[str]|None=None):
        raise NotImplementedError()


    def __call__(self, cmd:str|None=None) -> None:
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
        raise NotImplementedError
