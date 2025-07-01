#!/usr/bin/env python3
"""

"""
# ruff: noqa:
# mypy: disable-error-code="attr-defined"
# Imports:
from __future__ import annotations

# ##-- stdlib imports
import atexit#  for @atexit.register
import collections
import contextlib
import datetime
import enum
import faulthandler
import functools as ftz
import hashlib
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref

# ##-- end stdlib imports

# ##-- 2rd party imports
from jgdv import Proto
from jgdv.cli import errors
from jgdv.cli._interface import (EMPTY_CMD, EXTRA_KEY, ArgParserModel_p, ParamSpec_i,
                                 ParamSource_p, ParamSpec_p, ParseResult_d, PositionalParam_p)
from jgdv.cli.param_spec import HelpParam, ParamSpec, SeparatorParam, ParamProcessor
from jgdv.cli.parser_model import ParseType_e

# ##-- end 3rd party imports

# ##-- types
# isort: off
import abc
import collections.abc
from typing import TYPE_CHECKING, cast, assert_type, assert_never
from typing import Generic, NewType, Never
# Protocols:
from typing import Protocol, runtime_checkable
# Typing Decorators:
from typing import no_type_check, final, override, overload

if TYPE_CHECKING:
    from jgdv import Maybe
    from typing import Final
    from typing import ClassVar, Any, LiteralString
    from typing import Self, Literal
    from typing import TypeGuard
    from collections.abc import Iterable, Iterator, Callable, Generator
    from collections.abc import Sequence, Mapping, MutableMapping, Hashable

##--|

# isort: on
# ##-- end types

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

# Vars:
HELP            : Final[ParamSpec]     = HelpParam()
SEPARATOR       : Final[ParamSpec]     = SeparatorParam()
# Body:

@Proto(ArgParserModel_p)
class DootArgParserModel:
    """

    # {prog} {args} {cmd} {cmd_args}
    # {prog} {args} [{task} {tasks_args}] - implicit do cmd

    """

    type CmdName        = str
    type SubName        = str
    type SubConstraint  = tuple[str,...]
    type Sub_Params     = tuple[SubConstraint, list[ParamSpec_i]]

    args_initial         : tuple[str, ...]
    args_remaining       : list[str]
    data_cmds            : list[ParseResult_d]
    data_prog            : Maybe[ParseResult_d]
    data_subs            : list[ParseResult_d]
    specs_cmds           : dict[CmdName, list[ParamSpec_i]]
    specs_prog           : list[ParamSpec_i]
    specs_subs           : dict[SubName, list[ParamSpec_i]]

    _subs_constraints    : collections.defaultdict[CmdName, set[SubName]]
    _current_section     : Maybe[tuple[str, list[ParamSpec_i]]]
    _current_data        : Maybe[ParseResult_d]
    _separator           : ParamSpec_i
    _help                : ParamSpec_i
    _force_help          : bool
    _report              : dict
    _section_type        : Maybe[ParseType_e]
    _processor           : ParamProcessor

    def __init__(self) -> None:
        self._processor         = ParamSpec._processor
        self._separator         = SEPARATOR
        self._help              = HELP
        self._current_section   = None
        self._subs_constraints  = collections.defaultdict(set)
        self._force_help        = False
        self._section_type      = None
        self.args_initial       = ()
        self.args_remaining     = []
        self.args_remaining     = []
        self.data_cmds          = []
        self.data_prog          = None
        self.data_subs          = []
        self.specs_prog         = []
        self.specs_cmds         = {}
        self.specs_subs         = {}

    ##--| conditions

    def _has_more_args(self) -> bool:
        return bool(self.args_remaining)

    def _has_help_flag_at_tail(self) -> bool:
        return self._processor.matches_head(self._help,
                                            self.args_remaining[-1])

    def _prog_at_front(self) -> bool:
        match self.args_remaining:
            case ["python", *_]:
                return True
            case _:
                return False

    def _cmd_at_front(self) -> bool:
        return self.args_remaining[0] in self.specs_cmds

    def _sub_at_front(self) -> bool:
        return self.args_remaining[0] in self.specs_subs

    def _kwarg_at_front(self) -> bool:
        """ See if theres a kwarg to parse """
        params : list
        match self._current_section:
            case None:
                return False
            case _, [*params]:
                pass

        head = self.args_remaining[0]
        for param in params:
            match param:
                case PositionalParam_p():
                    continue
                case _:
                    if self._processor.matches_head(param, head):
                        return True
        else:
            return False

    def _posarg_at_front(self) -> bool:
        params : list
        match self._current_section:
            case None:
                return False
            case _, [*params]:
                pass

        head = self.args_remaining[0]
        for param in params:
            match param:
                case PositionalParam_p():
                    if self._processor.matches_head(param, head): # type: ignore[arg-type]
                        return True
                case _:
                    continue
        else:
            return False

    def _separator_at_front(self) -> bool:
        return self._processor.matches_head(self._separator,
                                            self.args_remaining[0])

    ##--| state actions

    def prepare_for_parse(self, *, prog:list, cmds:list, subs:list, raw_args:list[str]) -> None:
        logging.debug("Setting up Parsing : %s", raw_args)
        self.args_initial    = tuple(raw_args[:])
        self.args_remaining  = raw_args[:]
        self.specs_prog      = prog[:]
        self._prep_cmd_lookup(cmds)
        self._prep_sub_lookup(subs)

    def set_force_help(self) -> None:
        match self._help.consume(self.args_remaining):
            case dict(), int() as count:
                self._force_help = True
                self.args_remaining = self.args_remaining[count:]
            case _:
                pass

    def select_prog_spec(self) -> None:
        self._current_section = ("prog", sorted(self.specs_prog, key=ParamSpec.key_func))
        self._section_type = ParseType_e.prog

    def select_cmd_spec(self) -> None:
        head = self.args_remaining.pop(0)
        match self.specs_cmds.get(head, None):
            case None:
                raise ValueError()
            case [*params]:
                self._current_section = (head, sorted(params, key=ParamSpec.key_func))
                self._section_type = ParseType_e.cmd

    def select_sub_spec(self) -> None:
        last_cmd     = self.data_cmds[-1].name
        constraints  = self._subs_constraints[last_cmd]
        head         = self.args_remaining.pop(0)
        if head not in constraints:
            msg = "Sub Not Available for cmd"
            raise ValueError(msg, last_cmd, head)

        self._current_section = (head, sorted(self.specs_subs[head], key=ParamSpec.key_func))
        self._section_type = ParseType_e.sub

    def initialise_section(self) -> None:
        name      : str
        defaults  : dict
        match self._current_section:
            case str() as name, list() as params:
                defaults = ParamSpec.build_defaults(params)
            case None:
                raise ValueError()
        match self._section_type:
            case ParseType_e.sub:
                last_cmd            = self.data_cmds[-1].name
                self._current_data  = ParseResult_d(name=name, ref=last_cmd, args=defaults)
            case _:
                self._current_data  = ParseResult_d(name=name)

    def parse_kwarg(self) -> None:
        """ try each param until one works """
        params : list[ParamSpec_i]
        assert(self._current_data is not None)
        match self._current_section:
            case str(), list() as params:
                pass
            case x:
                raise TypeError(type(x))

        while bool(params):
            if isinstance(params[0], PositionalParam_p):
                return
            param = params.pop(0)
            match param.consume(self.args_remaining):
                case None:
                    continue
                case dict() as data, int() as count:
                    self._current_data.args.update(data)
                    self._current_data.non_default.update(data.keys())
                    self.args_remaining = self.args_remaining[count:]
                    return

    def parse_posarg(self) -> None:
        params : list[ParamSpec_i]
        assert(self._current_data is not None)
        match self._current_section:
            case _, list() as params:
                pass
            case x:
                raise TypeError(type(x))

        while bool(params):
            param = params.pop(0)
            if not isinstance(param, PositionalParam_p):
                continue
            match param.consume(self.args_remaining):
                case None:
                    continue
                case dict() as data, int() as count:
                    self._current_data.args.update(data)
                    self._current_data.non_default.update(data.keys())
                    self.args_remaining = self.args_remaining[count:]
                    return

    def clear_section(self) -> None:
        assert(self._current_data)
        self._current_section = None
        match self._section_type:
            case None:
                raise ValueError()
            case ParseType_e.prog:
                self.data_prog = self._current_data
            case ParseType_e.cmd:
                self.data_cmds.append(self._current_data)
            case ParseType_e.sub:
                self.data_subs.append(self._current_data)
        ##--|
        self._current_data = None

    def report(self) -> Maybe[dict]:
        """ Take the parsed results and return a nested dict """
        if (self.data_prog is None):
            return {
                "raw" : self.args_initial,
            }
        assert(bool(self.data_cmds))
        assert(bool(self.data_subs))
        result = {
            "raw"   : self.args_initial,
            "prog"  : self.data_prog.to_dict(),
            "cmds"  : {},
            "sub"   : {},
        }

        match self._force_help:
            case False:
                pass
            case True:
                pass

        self._report = result
        return None

    def cleanup(self) -> None:
        logging.debug("Cleaning up")
        self.args_initial    = ()
        self.args_remaining  = []
        self.specs_cmds      = {}
        self.specs_subs      = {}
    ##--| util

    def _prep_cmd_lookup(self, cmds:list[ParamSource_p]) -> None:
        """ get the param specs for each cmd """
        if not isinstance(cmds, list):
            msg = "cmds needs to be a list"
            raise TypeError(msg, cmds)

        for x in cmds:
            match x:
                case (str() as alias, ParamSource_p() as source):
                    self.specs_cmds[alias] = source.param_specs()
                    self.specs_cmds[source.name] = source.param_specs()
                case ParamSource_p() as source:
                    self.specs_cmds[source.name] = source.param_specs()
                case x:
                    raise TypeError(x)

    def _prep_sub_lookup(self, subs:list[ParamSource_p]) -> None:
        """ for each sub cmd, get it's param specs, but also register the parent cmd constraint """
        if not isinstance(subs, list):
            logging.info("No Subcmd Specs provided for parsing")
            return

        for x in subs:
            match x:
                case [*constraints], ParamSource_p() as source:
                    assert(all(isinstance(c, str) for c in constraints))
                    self.specs_subs[source.name] = source.param_specs()
                    for c in constraints:
                        self._subs_constraints[c].add(source.name)
                case x:
                    raise TypeError(type(x))
