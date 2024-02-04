## base_action.py -*- mode: python -*-
##-- imports
from __future__ import annotations

# import abc
import datetime
# import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
##-- end imports

printer = logmod.getLogger("doot._printer")

from time import sleep
import sys
import sh
import doot
from doot.structs import DootKey
from doot.errors import DootTaskError, DootTaskFailed
from doot._abstract import Action_p

@doot.check_protocol
class SpeakTimeAction(Action_p):
    """
    A Simple Action that announces the time
    Subclass this and override __call__ for your own actions.
    The arguments of the action are held in self.spec

    """
    _toml_kwargs = ["wait", "background"]
    mac_announce_args = ["-v", "Moira", "-r", "50", "The Time Is "]
    linux_announce_args = ["The Time Is "]
    time_format   = "%H:%M"

    def _current_time(self) -> str:
        now = datetime.datetime.now()
        return now.strftime(self.time_format)

    @DootKey.kwrap.args
    def __call__(self, spec, state, args):
        try:
            match sys.platform:
                case "linux":
                    return self._say_linux(spec, state)
                case "darwin":
                    return self._say_mac(spec, state)
                case _:
                    return False
        except sh.CommandNotFound as err:
            printer.error("Shell Commmand '%s' Not Action: %s", err.args[0], args)
            return False
        except sh.ErrorReturnCode:
            printer.error("Shell Command '%s' exited with code: %s for args: %s", args[0], result.exit_code, args)
            return False


    def _say_linux(self, spec, state:dict):
        cmd    = sh.espeak
        args   = (spec.args or self.mac_announce_args) + [self._current_time()]
        if spec.kwargs.on_fail(False, bool).wait():
            sleep(10)
        result = cmd(*args, _return_cmd=True, _bg=spec.kwargs.on_fail(False, bool).background())
        assert(result.exit_code == 0)
        printer.debug("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, cmd, args)
        printer.info("%s", result, extra={"colour":"reset"})
        return True


    def _say_mac(self, spec, state:dict):
        cmd    = sh.say
        args   = (spec.args or self.mac_announce_args) + [self._current_time()]
        if spec.kwargs.on_fail(False, bool).wait():
            sleep(10)
        result = cmd(*args, _return_cmd=True, _bg=spec.kwargs.on_fail(False, bool).background())
        assert(result.exit_code == 0)
        printer.debug("(%s) Shell Cmd: %s, Args: %s, Result:", result.exit_code, cmd, args)
        printer.info("%s", result, extra={"colour":"reset"})
        return True
