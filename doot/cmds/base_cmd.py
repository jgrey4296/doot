#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

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
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
# import more_itertools as mitz
# from boltons import
##-- end lib imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doot._abstract import Command_i
from doot.mixins.param_spec import ParamSpecMaker_m

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
            help_lines += map(str, sorted(filter(lambda x: not x.invisible,
                                            self.param_specs),
                                    key=key_func))

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
           self.build_param(name="help", default=False, prefix="--", invisible=True),
           self.build_param(name="debug", default=False, prefix="--", invisible=True)
           ]
