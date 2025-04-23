#!/usr/bin/env python3
"""

"""

# Imports:
from __future__ import annotations

# ##-- stdlib imports
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import typing
import weakref
from uuid import UUID, uuid1

# ##-- end stdlib imports

# ##-- 3rd party imports
from jgdv import Mixin, Proto
from jgdv.cli.param_spec.builder_mixin import ParamSpecMaker_m
# ##-- end 3rd party imports

# ##-- 1st party imports
import doot
from doot._abstract import Command_p, Command_d

# ##-- end 1st party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv.cli import ParamStruct_p
    from jgdv import Maybe, Lambda
    from jgdv.structs.chainguard import ChainGuard
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Never, Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

    from doot.errors import DootError
    type ListVal = str|Lambda|tuple[str,dict]

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

@Proto(Command_p, check=False)
@Mixin(ParamSpecMaker_m)
class BaseCommand(Command_d):
    """ Generic implementations of command methods """
    build_param : Callable

    def __init__(self, name:Maybe[str]=None):
        self._name = name

    @property
    def name(self) -> str:
        """get command name as used from command line"""
        return self._name or self.__class__.__name__.lower()

    @property
    def help(self) -> list[str]:
        help_lines : list[str] = [
            "", f"Command: {self.name} v{self._version}", "",
            *list(self._help or []),
        ]

        params = self.param_specs
        if bool(params):
            key_func = params[0].key_func
            help_lines += ["", "Params:"]
            help_lines += filter(bool, (x.help_str() for x in sorted(self.param_specs, key=key_func))) # type: ignore

        return help_lines

    @property
    def helpline(self) -> str:
        """ get just the first line of the help text """
        match self._help:
            case [x, *_]:
                return f" {self.name: <10} v{self._version:>5} : {x}"
            case _:
                return f" {self.name: <10} v{self._version:>5} :"

    @property
    def param_specs(self) -> list[ParamStruct_p]:
        """
        Provide parameter specs for parsing into doot.args.cmd
        """
        return [
           self.build_param(name="--help", default=False, implicit=True),
           self.build_param(name="--debug", default=False, implicit=True),
           ]

    def _print_text(self, text:Iterable[ListVal]) -> None:
        """ Utility method to print text out at the user level """
        match text:
            case str():
                text = [text]
            case [*_]:
                pass
            case x:
                 raise doot.errors.CommandError("Unknown type tried to be printed")
        for line in text:
            match line:
                case str():
                    doot.report.user(line)
                case (str() as s, dict() as d):
                    doot.report.user(s, extra=d)
                case None:
                    doot.report.user("")



    def shutdown(self, tasks:ChainGuard, plugins:ChainGuard, errored:Maybe[DootError]=None) -> None:
        pass
