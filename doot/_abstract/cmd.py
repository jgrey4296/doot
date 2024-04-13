##-- imports
from __future__ import annotations
import inspect
import sys
from collections import deque
from collections import defaultdict
import textwrap
from typing import TYPE_CHECKING
##-- end imports

from abc import abstractmethod
from tomlguard import TomlGuard

from doot._abstract.structs import ParamStruct_p

class Command_i:
    """
    holds command information and performs it
    """

    _name : None|str       = None # if not specified uses the class name
    _help : None|list[str] = None

    _version : str      = "0.1"

    @property
    @abstractmethod
    def name(self):
        """get command name as used from command line"""
        pass

    @property
    @abstractmethod
    def help(self) -> str:
        pass

    @property
    @abstractmethod
    def helpline(self) -> str:
        """ get just the first line of the help text """
        pass

    @abstractmethod
    def __call__(self, jobs:TomlGuard, plugins:TomlGuard):
        pass

    def shutdown(self, tasks, plugins, errored=None):
        """
          A Handler called on doot shutting down. only the triggered cmd's shutdown gets called
        """
        pass
