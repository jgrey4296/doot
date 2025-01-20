#!/usr/bin/env python3
"""

"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
import typing
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator,
                    Generic, Iterable, Iterator, Mapping, Match,
                    MutableMapping, Protocol, Sequence, Tuple, TypeAlias,
                    TypeGuard, TypeVar, cast, final, overload,
                    runtime_checkable)
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 1st party imports
import doot
from doot._abstract import Command_i
from doot.mixins.param_spec import ParamSpecMaker_m

# ##-- end 1st party imports

# ##-- types
# isort: off
if typing.TYPE_CHECKING:
   from jgdv import Maybe
   type ListVal = str|Lambda|tuple[str,dict]
# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
cmd_l = doot.subprinter("cmd")
##-- end logging

class BaseCommand(ParamSpecMaker_m, Command_i):
    """ Generic implementations of command methods """

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
            key_func = params[0].key_func
            help_lines += ["", "Params:"]
            help_lines += filter(bool, map(lambda x: x.help_str(), sorted(self.param_specs, key=key_func)))

        return "\n".join(help_lines)

    @property
    def helpline(self) -> str:
        """ get just the first line of the help text """
        if not bool(self._help):
            return f" {self.name: <10} v{self._version:>5} :"
        return f" {self.name: <10} v{self._version:>5} : {self._help[0]}"

    @property
    def param_specs(self) -> list[ParamStruct_p]:
        """
        Provide parameter specs for parsing into doot.args.cmd
        """
        return [
           self.build_param(name="help", default=False, prefix="--", implicit=True),
           self.build_param(name="debug", default=False, prefix="--", implicit=True)
           ]

    def _print_text(self, text:list[ListVal]) -> None:
        """ Utility method to print text out at the user level """
        for line in text:
            match line:
                case str():
                    cmd_l.user(line)
                case (str() as s, dict() as d):
                    cmd_l.user(s, extra=d)
                case None:
                    cmd_l.user("")
