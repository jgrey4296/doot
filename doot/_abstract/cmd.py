##-- imports
from __future__ import annotations
import inspect
import sys
from collections import deque
from collections import defaultdict
import textwrap
##-- end imports

from doot._abstract.parser import ParamSpecMaker_mixin

class Command_i(ParamSpecMaker_mixin):
    """
    holds command information and performs it
    """

    _name : None|str       = None # if not specified uses the class name
    _help : None|list[str] = None

    _version : str      = "0.1"
    def __init__(self, name=None):
        self._name = name

    @property
    def name(self):
        """get command name as used from command line"""
        return self._name or self.__class__.__name__.lower()

    @property
    def help(self) -> str:
        help_lines = ["", f"Command: {self.name} v{self._version}", ""]
        help_lines += self._help

        params = self.param_specs
        if bool(params):
            help_lines += ["", "Params:"]
            help_lines += filter(bool, (str(x) for x in self.param_specs))

        return "\n".join(help_lines)

    @property
    def helpline(self) -> str:
        """ get just the first line of the help text """
        if not bool(self._help):
            return f" {self.name: <10} v{self._version:>5} :"
        return f" {self.name: <10} v{self._version:>5} : {self._help[0]}"

    @property
    def param_specs(self) -> list:
        """
        Provide parameter specs for parsing into doot.args.cmd
        """
        return [
           self.make_param(name="help", default=False, prefix="--", invisible=True),
           self.make_param(name="debug", default=False, prefix="--", invisible=True)
           ]

    def __call__(self, taskers:Tomler, plugins:Tomler):
        raise NotImplementedError()
