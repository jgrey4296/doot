"""

"""
from __future__ import annotations
import sys

from doot._abstract.parser import DootParamSpec

class Overlord_i:
    """
    Main entrypoint for doot
    """

    def __init__(self, *, loaders:dict[str, Loader_i]=None,
                 configs:tuple[pl.Path|str]=('doot.toml', 'pyproject.toml'),
                 extra_config:dict|Tomler=None,
                 args:list=None):
        raise NotImplementedError()

    @staticmethod
    def print_version() -> str:
        raise NotImplementedError()

    @staticmethod
    def make_param(*args, **kwargs) -> DootParamSpec:
        return DootParamSpec(*args, **kwargs)

    def __call__(self, args):
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

    def shutdown(self):
        raise NotImplementedError
