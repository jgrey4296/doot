#!/usr/bin/env python3
"""

"""
##-- imports
from __future__ import annotations

import types
import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable)
from uuid import UUID, uuid1
from weakref import ref

##-- end imports

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

from doot.actions.interactive_cmd_action import Interactive
from types import FunctionType, MethodType
import os
import doot
from doot.actions.cmd_action import DootCmdAction
from doot.actions.force_cmd_action import ForceCmd

conda_exe        = os.environ['CONDA_EXE']

class CommanderMixin:

    def cmd(self, cmd:str|list|callable, *args, shell=False, save=None, **kwargs):
        raise DeprecationWarning("use make_cmd")

    def make_cmd(self, cmd:str|list|callable, *args, shell=False, save=None, **kwargs):
        logging.debug("Cmd: %s Args: %s kwargs: %s", cmd, args or [], kwargs or {})
        match cmd:
            case FunctionType() | MethodType():
                action = (cmd, args, kwargs)
            case str() | pl.Path():
                action = [cmd, *args]
            case list():
                assert(not bool(args))
                action = [x for x in cmd if x is not None]
            case _:
                raise TypeError("Unexpected action form: ", cmd)

        return DootCmdAction(action, shell=shell, save_out=save, **kwargs)

    def force(self, cmd:list|callable, *args, handler=None, shell=False, save=None, **kwargs):
        raise DeprecationWarning("use make_force")

    def make_force(self, cmd:list|callable, *args, handler=None, shell=False, save=None, **kwargs):
        logging.debug("Forcing Cmd: %s Args: %s kwargs: %s", cmd, args or [], kwargs or {})
        match cmd:
            case FunctionType() | MethodType():
                action = (cmd, list(args), kwargs)
            case list():
                assert(not bool(args))
                assert(not bool(kwargs))
                action = [x for x in cmd if x is not None]
            case _:
                raise TypeError("Unexpected action form: ", cmd)

        return ForceCmd(action, shell=shell, handler=handler, save_out=save)

    def shell(self, cmd:list|callable, *args, **kwargs):
        raise DeprecationWarning("use make_shell")

    def make_shell(self, cmd:list|callable, *args, **kwargs):
        return self.make_cmd(cmd, *args, shell=True, **kwargs)

    def interact(self, cmd:list|callable, *args, save=None, **kwargs):
        raise DeprecationWarning("use make_interact")

    def make_interact(self, cmd:list|callable, *args, save=None, **kwargs):
        match cmd:
            case FunctionType():
                action = (cmd, list(args), kwargs)
            case str():
                action = [cmd, *args]
            case list():
                assert(not bool(args))
                assert(not bool(kwargs))
                action = [x for x in cmd if x is not None]
            case _:
                raise TypeError("Unexpected action form: ", cmd)
        return Interactive(action, shell=False, save_out=save)

    def regain_focus(self, prog="iTerm"):
        """
        Applescript command to regain focus for if you lose it
        """
        return self.make_cmd(["osascript", "-e", f"tell application \"{prog}\"", "-e", "activate", "-e", "end tell"])

    def say(self, *text, voice="Moira"):
        raise DeprecationWarning("use make_say")

    def make_say(self, *text, voice="Moira"):
        cmd = ["say", "-v", voice, "-r", "50"]
        cmd += text
        return DootCmdAction(cmd, shell=False)

    def in_conda(self, env, *args):
        return DootCmdAction([conda_exe, "run", "-n", env, *args], shell=False)
