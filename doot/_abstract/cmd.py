##-- imports
from __future__ import annotations
import inspect
import sys
from collections import deque
from collections import defaultdict
import textwrap
##-- end imports

class Command_i:
    """
    holds command information and performs it
    """

    _name : None|str       = None # if not specified uses the class name
    _help : None|list[str] = None

    def __init__(self, name=None):
        self._name = name

    @property
    def name(self):
        """get command name as used from command line"""
        return self._name or self.__class__.__name__.lower()

    @property
    def help(self) -> str:
        return "\n".join(self._help)

    @property
    def param_specs(self) -> list:
        """
        Provide parameter specs for parsing into doot.args.cmd
        """
        return []

    def __call__(self, taskers, plugins):
        raise NotImplementedError()
