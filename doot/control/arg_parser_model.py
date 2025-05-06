#!/usr/bin/env python3
"""


"""
# ruff: noqa:
# mypy: disable-error-code="attr-defined"
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
import collections
import contextlib
import hashlib
from copy import deepcopy
from uuid import UUID, uuid1
from weakref import ref
import atexit # for @atexit.register
import faulthandler
# ##-- end stdlib imports

from statemachine import State, StateMachine
from statemachine.exceptions import TransitionNotAllowed
from statemachine.states import States

from jgdv.cli import errors
from jgdv.cli.param_spec import HelpParam, ParamSpec, SeparatorParam
from jgdv.cli.parse_machine_base import ParseMachineBase
from jgdv.cli._interface import ParseResult_d, EXTRA_KEY, EMPTY_CMD
from jgdv.cli._interface import ParamStruct_p, ArgParser_p, ParamSource_p

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
SEPERATOR       : Final[ParamSpec]     = SeparatorParam()
# Body:

class DootArgParser:
    """

    # {prog} {args} {cmd} {cmd_args}
    # {prog} {args} [{task} {tasks_args}] - implicit do cmd

    """
    _initial_args      : list[str]
    _remaining_args    : list[str]
    _head_specs        : list[ParamSpec]
    _cmd_specs         : dict[str, list[ParamStruct_p]]
    _subcmd_specs      : dict[str, tuple[str, list[ParamStruct_p]]]
    head_result        : Maybe[ParseResult_d]
    cmd_result         : Maybe[ParseResult_d]
    subcmd_results     : list[ParseResult_d]
    extra_results      : ParseResult_d
    _force_help        : bool

    def __init__(self) -> None:
        self._remaining_args    = []
        self._initial_args      = []
        self._remaining_args    = []
        self._head_specs        = []
        self._cmd_specs         = {}
        self._subcmd_specs      = {}
        self.head_result        = None
        self.cmd_result         = None
        self.subcmd_results     = []
        self.extra_results      = ParseResult_d(EXTRA_KEY)
        self._force_help        = False


    def _parse_fail_cond(self) -> bool:
        return False

    def _has_no_more_args_cond(self) -> bool:
        return not bool(self._remaining_args)

    @ParseMachineBase.finish._transitions.before
    def all_args_consumed_val(self) -> None:
        if bool(self._remaining_args):
            msg = "Not All Args Were Consumed"
            raise errors.ArgParseError(msg, self._remaining_args)

    @ParseMachineBase.Prepare.enter
    def _setup(self, args:list[str], head_specs:list, cmds:list[ParamSource_p], subcmds:list[tuple[str, ParamSource_p]]) -> None:
        """
          Parses the list of arguments against available registered parameter head_specs, cmds, and tasks.
        """
        logging.debug("Setting up Parsing : %s", args)
        head_specs                                  = head_specs or []
        cmds                                        = cmds or []
        subcmds                                     = subcmds or []
        self._initial_args                          = args[:]
        self._remaining_args                        = args[:]
        self._head_specs : list[ParamSpec]          = head_specs

        if not isinstance(cmds, list):
            msg = "cmds needs to be a list"
            raise TypeError(msg, cmds)

        for x in cmds:
            match x:
                case (str() as alias, ParamSource_p() as source):
                    self._cmd_specs[alias] = source.param_specs()
                case ParamSource_p():
                    self._cmd_specs[x.name] = x.param_specs()
                case x:
                    raise TypeError(x)

        match subcmds:
            case [*xs]:
                self._subcmd_specs = {y.name:(x, y.param_specs()) for x,y in xs}
            case _:
                logging.info("No Subcmd Specs provided for parsing")
                self._subcmd_specs = {}

        self.head_result       = None
        self.cmd_result        = None
        self.subcmd_results    = []
        self.extra_results     = ParseResult_d(EXTRA_KEY)
        self._force_help       = False

    @ParseMachineBase.Cleanup.enter
    def _cleanup(self) -> None:
        logging.debug("Cleaning up")
        self._initial_args      = []
        self._remaining_args    = []
        self._cmd_specs         = {}
        self._subcmd_specs      = {}

    @ParseMachineBase.CheckForHelp.enter
    def help_flagged(self) -> None:
        logging.debug("Checking for Help Flag")
        match HELP.consume(self._remaining_args[-1:]):
            case None:
                self._force_help = False
            case _:
                self._force_help = True
                self._remaining_args.pop()

    @ParseMachineBase.Head.enter
    def _parse_head(self) -> None:
        """ consume arguments for doot actual """
        logging.debug("Head Parsing: %s", self._remaining_args)
        if not bool(self._head_specs):
            self.head_result = ParseResult_d(name=self._remaining_args.pop(0))
            return
        head_specs       = sorted(self._head_specs, key=ParamSpec.key_func)
        defaults : dict  = ParamSpec.build_defaults(head_specs)
        self.head_result = ParseResult_d("_head_", defaults)
        self._parse_params_unordered(self.head_result, head_specs)

    @ParseMachineBase.Cmd.enter
    def _parse_cmd(self) -> None:
        """ consume arguments for the command being run """
        logging.debug("Cmd Parsing: %s", self._remaining_args)
        if not bool(self._cmd_specs):
            self.cmd_result = ParseResult_d(EMPTY_CMD, {})
            return

        # Determine cmd
        cmd_name = self._remaining_args[0]
        if cmd_name not in self._cmd_specs:
            self.cmd_result = ParseResult_d(EMPTY_CMD, {})
            return

        logging.info("Cmd matches: %s", cmd_name)
        self._remaining_args.pop(0)
        # get its specs
        cmd_specs : list[ParamStruct_p] = sorted(self._cmd_specs[cmd_name], key=ParamSpec.key_func)
        defaults  : dict                = ParamSpec.build_defaults(cmd_specs)
        self.cmd_result                 = ParseResult_d(cmd_name, defaults)
        self._parse_params_unordered(self.cmd_result, cmd_specs) # type: ignore

    @ParseMachineBase.SubCmd.enter
    def _parse_subcmd(self) -> None:
        """ consume arguments for tasks """
        if not bool(self._subcmd_specs):
            return
        logging.debug("SubCmd Parsing: %s", self._remaining_args)
        assert(self.cmd_result is not None)
        active_cmd = self.cmd_result.name
        last = None
        # Determine subcmd
        while (bool(self._remaining_args)
               and last != (sub_name:=self._remaining_args[0])
               ):
            if self._parse_separator():
                continue
            else:
                self._remaining_args.pop(0)

            logging.debug("Sub Cmd: %s", sub_name)
            last = sub_name
            match self._subcmd_specs.get(sub_name, None):
                case cmd_constraint, params if active_cmd in [cmd_constraint, EMPTY_CMD]:
                    sub_specs        = sorted(params, key=ParamSpec.key_func)
                    defaults : dict  = ParamSpec.build_defaults(sub_specs)
                    sub_result       = ParseResult_d(sub_name, defaults)
                    self._parse_params_unordered(sub_result, sub_specs) # type: ignore
                    self.subcmd_results.append(sub_result)
                case _, _:
                    pass
                case _:
                    msg = "Unrecognised SubCmd"
                    raise errors.SubCmdParseError(msg, sub_name)

    @ParseMachineBase.Extra.enter
    def _parse_extra(self) -> None:
        logging.debug("Extra Parsing: %s", self._remaining_args)
        self._remaining_args = []

    def _parse_params(self, res:ParseResult_d, params:list[ParamSpec]) -> None:
        for param in params:
            match param.consume(self._remaining_args):
                case None:
                    logging.debug("Skipping Parameter: %s", param.name)
                case data, count:
                    logging.debug("Consuming Parameter: %s", param.name)
                    self._remaining_args = self._remaining_args[count:]
                    res.args.update(data)
                    res.non_default.add(param.name)

    def _parse_params_unordered(self, res:ParseResult_d, params:list[ParamSpec]) -> None:
        logging.debug("Parsing Params Unordered: %s", params)
        non_positional = [x for x in params if not x.positional]
        positional     = [x for x in params if x.positional]

        def consume_it(x:ParamSpec) -> None:
            # TODO refactor this as a partial
            logging.debug("Consume it: %s", x.name)
            match x.consume(self._remaining_args):
                case None:
                    msg = "Failed to consume"
                    raise errors.ParseError(msg, x.name)
                case data, count:
                    logging.debug("Consuming Parameter: %s", x.name)
                    self._remaining_args = self._remaining_args[count:]
                    res.args.update(data)
                    res.non_default.add(x.name)

        # Parse non-positional params
        while bool(non_positional) and bool(self._remaining_args):
            match [x for x in non_positional if x.matches_head(self._remaining_args[0])]:
                case []:
                    non_positional = []
                case [x]:
                    consume_it(x)
                    non_positional.remove(x)
                case [*xs]:
                    msg = "Too many potential non-positional params"
                    raise errors.ParseError(msg, xs)
        else:
            logging.debug("Finished consuming non-positional")

        # Parse positional params
        while bool(positional) and bool(self._remaining_args):
            match [x for x in positional if x.matches_head(self._remaining_args[0])]:
                case []:
                    positional = []
                case [x, *xs]:
                    consume_it(x)
                    positional.remove(x)
        else:
            logging.debug("Finished Consuming Positional")

    def _parse_separator(self) -> bool:
        match SEPERATOR.consume(self._remaining_args):
            case None:
                return False
            case _:
                logging.debug("----")
                self._remaining_args.pop(0)
                return True

    def report(self) -> Maybe[dict]:
        """ Take the parsed results and return a nested dict """

        match self._force_help:
            case False:
                cmd_result = self.cmd_result
            case True if self.cmd_result is None:
                assert(self.head_result is not None)
                self.head_result.args['help'] = True
                cmd_result = ParseResult_d(EMPTY_CMD)
            case True if self.cmd_result.name == EMPTY_CMD:
                cmd_result = ParseResult_d("help", {"target":None, "args": self.cmd_result.args}, self.cmd_result.non_default)
            case True:
                cmd_result = ParseResult_d("help", {"target":self.cmd_result.name, "args": self.cmd_result.args}, self.cmd_result.non_default)

        result = {
            "head"  : self.head_result.to_dict() if self.head_result else {},
            "cmd"   : cmd_result.to_dict() if cmd_result else {},
            "sub"   : {y['name']:y['args'] for x in self.subcmd_results if (y:=x.to_dict()) is not None},
            "extra" : self.extra_results.to_dict(),
        }
        return result
