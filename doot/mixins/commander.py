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

from types import FunctionType, MethodType
import os
import doot
from doot.utils.task_ext import DootCmdAction

conda_exe        = os.environ['CONDA_EXE']

class CommanderMixin:

    def cmd(self, cmd:list|callable, *args, shell=False, save=None, **kwargs):
        logging.debug("Cmd: %s Args: %s kwargs: %s", cmd, args, kwargs)
        match cmd:
            case FunctionType() | MethodType():
                action = (cmd, list(args), kwargs)
            case str() | pl.Path():
                action = [cmd, *args]
            case list():
                assert(not bool(args))
                assert(not bool(kwargs))
                action = cmd
            case _:
                raise TypeError("Unexpected action form: ", cmd)

        return DootCmdAction(action, shell=shell, save_out=save)

    def force(self, cmd:list|callable, *args, handler=None, shell=False, save=None, **kwargs):
        logging.debug("Forcing Cmd: %s Args: %s kwargs: %s", cmd, args, kwargs)
        match cmd:
            case FunctionType() | MethodType():
                action = (cmd, list(args), kwargs)
            case list():
                assert(not bool(args))
                assert(not bool(kwargs))
                action = cmd
            case _:
                raise TypeError("Unexpected action form: ", cmd)

        return ForceCmd(action, shell=shell, handler=handler, save_out=save)

    def shell(self, cmd:list|callable, *args, **kwargs):
        return self.cmd(cmd, *args, shell=True, **kwargs)

    def interact(self, cmd:list|callable, *args, save=None, **kwargs):
        match cmd:
            case FunctionType():
                action = (cmd, list(args), kwargs)
            case str():
                action = [cmd, *args]
            case list():
                assert(not bool(args))
                assert(not bool(kwargs))
                action = cmd
            case _:
                raise TypeError("Unexpected action form: ", cmd)
        return Interactive(action, shell=False, save_out=save)

    def regain_focus(self, prog="iTerm"):
        """
        Applescript command to regain focus for if you lose it
        """
        return self.cmd(["osascript", "-e", f"tell application \"{prog}\"", "-e", "activate", "-e", "end tell"])

    def say(self, *text, voice="Moira"):
        cmd = ["say", "-v", voice, "-r", "50"]
        cmd += text
        return DootCmdAction(cmd, shell=False)

    def in_conda(self, env, *args):
        return DootCmdAction([conda_exe, "run", "-n", env, *args], shell=False)
