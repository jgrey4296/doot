##-- imports
from __future__ import annotations
import inspect
import sys
from collections import deque
from collections import defaultdict
import textwrap
##-- end imports

from doot._abstract.parser import DootParamSpec

class Command_i:
    """
    holds command information and performs it
    """

    _name : None|str       = None # if not specified uses the class name
    _help : None|list[str] = None

    @staticmethod
    def make_param(*args, **kwargs) -> DootParamSpec:
        return DootParamSpec(*args, **kwargs)

    def __init__(self, name=None):
        self._name = name

    @property
    def name(self):
        """get command name as used from command line"""
        return self._name or self.__class__.__name__.lower()

    @property
    def help(self) -> str:
        help_lines = ["", f"Command: {self.name}", ""]
        help_lines += self._help

        params = self.param_specs
        if bool(params):
            help_lines += ["", "Params:"]
            help_lines += sorted(str(x) for x in self.param_specs)

        return "\n".join(help_lines)

    @property
    def helpline(self) -> str:
        if not bool(self._help):
            return f" {self.name: <10} :"
        return f" {self.name: <10} : {self._help[0]}"

    @property
    def param_specs(self) -> list:
        """
        Provide parameter specs for parsing into doot.args.cmd
        """
        return [
            self.make_param(name="help", default=False, prefix="--")
            ]

    def __call__(self, taskers:Tomler, plugins:Tomler):
        raise NotImplementedError()
