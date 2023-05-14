##-- imports
from __future__ import annotations
import inspect
import sys
from collections import deque
from collections import defaultdict
import textwrap
##-- end imports

class DootCommand_i:
    """
    holds command information and performs it
    """

    name = None # if not specified uses the class name

    def __init__(self, name=None):
        self._name = name

    @property
    def name(self):
        """get command name as used from command line"""
        return self._name or self.__class__.__name__.lower()

    @property
    def help(self) -> str:
        return ""

    @property
    def param_specs(self) -> list:
        return []

    def __call__(self, taskers, plugins):
        pass
